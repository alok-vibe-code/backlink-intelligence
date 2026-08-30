from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Annotated, Callable, Literal
from urllib.parse import urlencode
from urllib.request import Request as URLRequest
from urllib.request import urlopen

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import __version__
from .analysis import AnalysisConfig, PlacementAnalyzer
from .models import PageEvidence, PlacementSuggestion, TextSegment
from .safety import UnsafeURLError, validate_public_url

API_VERSION = "1"
LOGGER = logging.getLogger("backlink_intelligence.api")
LOGGER.setLevel(logging.INFO)


def _csv_environment(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        value.strip().lower()
        for value in os.getenv(name, default).split(",")
        if value.strip()
    )


class APISettings:
    def __init__(self) -> None:
        self.environment = os.getenv("BI_ENVIRONMENT", "development").strip().lower()
        self.allowed_origins = _csv_environment(
            "BI_ALLOWED_ORIGINS", "https://alokblog.com"
        )
        self.allowed_hosts = _csv_environment("BI_ALLOWED_HOSTS", "api.alokblog.com")
        self.turnstile_secret = os.getenv("BI_TURNSTILE_SECRET", "").strip()
        self.turnstile_hostname = os.getenv(
            "BI_TURNSTILE_HOSTNAME", "alokblog.com"
        ).strip().lower()
        self.rate_limit = self._integer("BI_RATE_LIMIT_PER_HOUR", 5, 1, 100)
        self.max_concurrency = self._integer("BI_MAX_CONCURRENCY", 2, 1, 8)
        self.analysis_timeout = self._integer("BI_ANALYSIS_TIMEOUT", 35, 10, 90)

    @staticmethod
    def _integer(name: str, default: int, minimum: int, maximum: int) -> int:
        try:
            value = int(os.getenv(name, str(default)))
        except ValueError:
            return default
        return min(max(value, minimum), maximum)

    @property
    def production(self) -> bool:
        return self.environment == "production"


SETTINGS = APISettings()


class APIError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


URLField = Annotated[str, Field(min_length=10, max_length=2048)]


class PlaceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_url: URLField
    target_url: URLField
    anchor: Annotated[str, Field(min_length=2, max_length=120)]
    challenge_token: Annotated[str, Field(min_length=1, max_length=4096)]

    @model_validator(mode="after")
    def validate_urls(self) -> "PlaceRequest":
        try:
            source = validate_public_url(self.source_url, resolve_dns=False)
            target = validate_public_url(self.target_url, resolve_dns=False)
        except UnsafeURLError as exc:
            raise ValueError(str(exc)) from exc
        if source == target:
            raise ValueError("Source URL and target URL must be different.")
        self.source_url = source
        self.target_url = target
        return self


class SegmentResponse(BaseModel):
    type: Literal["text", "link"]
    text: str
    url: str | None = None

    @model_validator(mode="after")
    def validate_segment(self) -> "SegmentResponse":
        if not self.text:
            raise ValueError("Segment text must not be empty.")
        if self.type == "link":
            if not self.url:
                raise ValueError("Link segments require a URL.")
            self.url = validate_public_url(self.url, resolve_dns=False)
        elif self.url is not None:
            raise ValueError("Text segments must not include a URL.")
        return self


class OpportunityResponse(BaseModel):
    rank: int
    paragraph_index: int
    score: float
    context_level: Literal["low", "medium", "high", "very_high"]
    destination_score: float
    destination_fit: Literal["low", "medium", "high", "very_high"]
    requested_anchor: str
    suggested_anchor: str
    strategy: Literal["minimal_insertion", "contextual_sentence"]
    recommendation_status: Literal["recommended", "manual_review"]
    review_required: bool
    intervention: Literal["low", "medium", "high"]
    preservation_percent: float
    before_text: str
    after_text: str
    after_segments: list[SegmentResponse]
    reasons: list[str]
    warnings: list[str]

    @model_validator(mode="after")
    def validate_segments(self) -> "OpportunityResponse":
        if not self.after_segments:
            raise ValueError("Structured after_segments are required.")
        if "".join(segment.text for segment in self.after_segments) != self.after_text:
            raise ValueError("Structured segments must reconstruct after_text exactly.")
        if sum(segment.type == "link" for segment in self.after_segments) != 1:
            raise ValueError("Exactly one link segment is required.")
        if self.review_required != (self.recommendation_status == "manual_review"):
            raise ValueError("Recommendation status and review requirement disagree.")
        return self


class PageSummary(BaseModel):
    url: str
    final_url: str
    title: str
    status_code: int


class PlaceResponse(BaseModel):
    success: Literal[True] = True
    status: Literal["completed", "no_suitable_placement"]
    request_id: str
    api_version: Literal["1"] = "1"
    engine_version: str
    source: PageSummary
    target: PageSummary
    opportunities: list[OpportunityResponse]
    analysis_warnings: list[str]

    @model_validator(mode="after")
    def validate_outcome(self) -> "PlaceResponse":
        if len(self.opportunities) > 3:
            raise ValueError("The public beta returns at most three opportunities.")
        if self.status == "no_suitable_placement" and self.opportunities:
            raise ValueError("A no-match response must not contain opportunities.")
        if self.status == "completed" and not self.opportunities:
            raise ValueError("A completed response must contain an opportunity.")
        for opportunity in self.opportunities:
            link_url = next(
                segment.url
                for segment in opportunity.after_segments
                if segment.type == "link"
            )
            if link_url != self.target.url:
                raise ValueError("The structured link URL must equal the target URL.")
        return self


def _error_payload(request_id: str, code: str, message: str) -> dict:
    return {
        "success": False,
        "request_id": request_id,
        "api_version": API_VERSION,
        "error": {"code": code, "message": message},
    }


class InMemoryProtection:
    def __init__(self) -> None:
        self.rate_windows: dict[str, deque[float]] = defaultdict(deque)
        self.active_ips: set[str] = set()
        self.lock = asyncio.Lock()
        self.semaphore = asyncio.Semaphore(SETTINGS.max_concurrency)
        self.salt = os.urandom(32)

    def key(self, request: Request) -> str:
        address = request.client.host if request.client else "unknown"
        return hashlib.sha256(self.salt + address.encode("utf-8", "replace")).hexdigest()

    async def reserve(self, key: str) -> None:
        now = time.monotonic()
        async with self.lock:
            window = self.rate_windows[key]
            while window and now - window[0] >= 3600:
                window.popleft()
            if len(window) >= SETTINGS.rate_limit:
                raise APIError(429, "rate_limited", "The hourly analysis limit has been reached.")
            if key in self.active_ips:
                raise APIError(503, "service_busy", "An analysis is already running for this connection.")
            self.active_ips.add(key)

        try:
            await asyncio.wait_for(self.semaphore.acquire(), timeout=0.05)
        except TimeoutError as exc:
            async with self.lock:
                self.active_ips.discard(key)
            raise APIError(503, "service_busy", "The analysis service is currently busy.") from exc

        async with self.lock:
            self.rate_windows[key].append(now)

    async def release(self, key: str) -> None:
        self.semaphore.release()
        async with self.lock:
            self.active_ips.discard(key)


PROTECTION = InMemoryProtection()
ANALYSIS_EXECUTOR = ThreadPoolExecutor(
    max_workers=SETTINGS.max_concurrency,
    thread_name_prefix="backlink-analysis",
)
USED_CHALLENGES: dict[str, float] = {}


def _verify_turnstile_remote(token: str) -> dict:
    body = urlencode(
        {"secret": SETTINGS.turnstile_secret, "response": token}
    ).encode("ascii")
    request = URLRequest(
        "https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=8) as response:
        raw = response.read(32_769)
    if len(raw) > 32_768:
        raise APIError(503, "challenge_failed", "Challenge verification was unavailable.")
    return json.loads(raw.decode("utf-8"))


def verify_challenge(token: str) -> bool:
    if not SETTINGS.turnstile_secret:
        return not SETTINGS.production

    token_hash = hashlib.sha256(token.encode("utf-8", "replace")).hexdigest()
    now = time.time()
    for old_hash, expires_at in list(USED_CHALLENGES.items()):
        if expires_at <= now:
            del USED_CHALLENGES[old_hash]
    if token_hash in USED_CHALLENGES:
        return False

    try:
        result = _verify_turnstile_remote(token)
        challenge_time = datetime.fromisoformat(
            str(result.get("challenge_ts", "")).replace("Z", "+00:00")
        )
    except (APIError, OSError, ValueError, TypeError, json.JSONDecodeError):
        return False
    age = datetime.now(timezone.utc) - challenge_time.astimezone(timezone.utc)
    valid = bool(
        result.get("success")
        and str(result.get("hostname", "")).lower() == SETTINGS.turnstile_hostname
        and str(result.get("action", "")) == "backlink_intelligence"
        and -60 <= age.total_seconds() <= 300
    )
    if valid:
        USED_CHALLENGES[token_hash] = now + 300
    return valid


def challenge_verifier() -> Callable[[str], bool]:
    return verify_challenge


async def _release_when_finished(future: asyncio.Future, key: str) -> None:
    try:
        await future
    except BaseException:
        pass
    finally:
        await PROTECTION.release(key)


def _page_summary(page: PageEvidence) -> PageSummary:
    return PageSummary(
        url=page.requested_url,
        final_url=page.final_url,
        title=page.title,
        status_code=page.status_code,
    )


def _segment_response(segment: TextSegment) -> SegmentResponse:
    return SegmentResponse(
        type=segment.type,
        text=segment.text,
        url=segment.url if segment.type == "link" else None,
    )


def _opportunity_response(
    item: PlacementSuggestion, normalized_target_url: str
) -> OpportunityResponse:
    response = OpportunityResponse(
        rank=item.rank,
        paragraph_index=item.paragraph_index,
        score=item.score,
        context_level=item.context_level,
        destination_score=item.destination_score,
        destination_fit=item.destination_fit,
        requested_anchor=item.requested_anchor,
        suggested_anchor=item.suggested_anchor,
        strategy=item.strategy,
        recommendation_status=item.recommendation_status,
        review_required=item.review_required,
        intervention=item.intervention,
        preservation_percent=item.preservation_percent,
        before_text=item.before,
        after_text=item.after_text,
        after_segments=[_segment_response(segment) for segment in item.after_segments],
        reasons=item.reasons,
        warnings=item.warnings,
    )
    link_url = next(
        segment.url for segment in response.after_segments if segment.type == "link"
    )
    if link_url != normalized_target_url:
        raise APIError(
            500,
            "internal_error",
            "The analysis returned an invalid target link.",
        )
    return response


def _analysis_failure(source: PageEvidence, target: PageEvidence) -> APIError:
    page = source if source.status_code != 200 else target
    role = "source" if page is source else "target"
    error = page.error
    if "RobotsDeniedError" in error:
        return APIError(403, "crawl_blocked", "The publisher's robots policy blocks analysis.")
    if "UnsupportedContentError" in error:
        return APIError(415, "unsupported_content", "The page is not supported HTML content.")
    if "UnsafeURLError" in error:
        return APIError(400, "unsafe_url", "The submitted URL did not pass the public-network safety check.")
    code = "source_unavailable" if role == "source" else "target_unavailable"
    return APIError(422, code, f"The {role} page could not be analyzed.")


app = FastAPI(
    title="Backlink Intelligence API",
    version=API_VERSION,
    docs_url=None if SETTINGS.production else "/docs",
    redoc_url=None,
    openapi_url=None if SETTINGS.production else "/openapi.json",
)


@app.middleware("http")
async def security_and_observability(request: Request, call_next):
    request_id = uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.monotonic()
    origin = request.headers.get("origin", "").lower()
    host = request.headers.get("host", "").split(":", 1)[0].lower()

    if request.url.path != "/health":
        if SETTINGS.production and host not in SETTINGS.allowed_hosts:
            return JSONResponse(
                _error_payload(request_id, "invalid_request", "Request host is not allowed."),
                status_code=400,
            )
        if origin and origin not in SETTINGS.allowed_origins:
            return JSONResponse(
                _error_payload(request_id, "invalid_request", "Request origin is not allowed."),
                status_code=403,
            )
        if SETTINGS.production and not origin:
            return JSONResponse(
                _error_payload(request_id, "invalid_request", "Request origin is required."),
                status_code=403,
            )

    if request.method == "OPTIONS":
        response: Response = Response(status_code=204)
    else:
        response = await call_next(request)
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Request-ID"] = request_id
    if origin in SETTINGS.allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Content-Type"
        response.headers["Vary"] = "Origin"
    LOGGER.info(
        "request_id=%s status=%s duration_ms=%d api_version=%s engine_version=%s",
        request_id,
        response.status_code,
        int((time.monotonic() - started) * 1000),
        API_VERSION,
        __version__,
    )
    return response


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    return JSONResponse(
        _error_payload(request.state.request_id, exc.code, exc.message),
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    del exc
    return JSONResponse(
        _error_payload(
            request.state.request_id,
            "invalid_request",
            "The request body did not match the v1 API contract.",
        ),
        status_code=422,
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    LOGGER.error(
        "request_id=%s status=500 code=internal_error exception=%s",
        request.state.request_id,
        exc.__class__.__name__,
    )
    return JSONResponse(
        _error_payload(
            request.state.request_id,
            "internal_error",
            "The analysis could not be completed.",
        ),
        status_code=500,
    )


@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "api_version": API_VERSION,
        "engine_version": __version__,
    }


@app.post("/v1/place", response_model=PlaceResponse)
async def place(
    payload: PlaceRequest,
    request: Request,
    verifier=Depends(challenge_verifier),
) -> PlaceResponse:
    request_id = request.state.request_id
    if not verifier(payload.challenge_token):
        raise APIError(403, "challenge_failed", "The anti-abuse challenge could not be verified.")

    key = PROTECTION.key(request)
    await PROTECTION.reserve(key)
    release_now = True
    try:
        analyzer = PlacementAnalyzer(AnalysisConfig.from_environment())
        loop = asyncio.get_running_loop()
        analysis_future = loop.run_in_executor(
            ANALYSIS_EXECUTOR,
            analyzer.analyze,
            payload.source_url,
            payload.target_url,
            payload.anchor,
        )
        try:
            analysis = await asyncio.wait_for(
                asyncio.shield(analysis_future),
                timeout=SETTINGS.analysis_timeout,
            )
        except TimeoutError as exc:
            release_now = False
            asyncio.create_task(_release_when_finished(analysis_future, key))
            raise APIError(504, "analysis_timeout", "The analysis exceeded the time limit.") from exc
        if analysis.status == "failed":
            raise _analysis_failure(analysis.source, analysis.target)

        return PlaceResponse(
            status=analysis.status,
            request_id=request_id,
            engine_version=__version__,
            source=_page_summary(analysis.source),
            target=_page_summary(analysis.target),
            opportunities=[
                _opportunity_response(item, payload.target_url)
                for item in analysis.opportunities
            ],
            analysis_warnings=analysis.analysis_warnings,
        )
    finally:
        if release_now:
            await PROTECTION.release(key)
