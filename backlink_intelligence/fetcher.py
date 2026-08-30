from __future__ import annotations

import gzip
import io
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .html_utils import parse_page
from .models import PageEvidence
from .safety import UnsafeURLError, validate_public_url


@dataclass(slots=True)
class FetchConfig:
    timeout: float = 12.0
    max_bytes: int = 2_000_000
    max_redirects: int = 5
    user_agent: str = "BacklinkIntelligence/1.0 (+https://github.com/alok-vibe-code/backlink-intelligence)"


class SafeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, max_redirects: int) -> None:
        super().__init__()
        self.max_redirects = max_redirects
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > self.max_redirects:
            raise UnsafeURLError("Redirect limit exceeded.")
        validate_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _decode_body(raw: bytes, encoding_header: str, content_type: str) -> str:
    if "gzip" in encoding_header.lower():
        raw = gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
    charset = "utf-8"
    marker = "charset="
    if marker in content_type.lower():
        charset = content_type.lower().split(marker, 1)[1].split(";", 1)[0].strip() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def fetch_page(url: str, config: FetchConfig | None = None) -> PageEvidence:
    config = config or FetchConfig()
    validate_public_url(url)
    redirect_handler = SafeRedirectHandler(config.max_redirects)
    opener = build_opener(redirect_handler)
    request = Request(url, headers={"User-Agent": config.user_agent, "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1", "Accept-Encoding": "gzip"})
    try:
        with opener.open(request, timeout=config.timeout) as response:
            final_url = response.geturl()
            validate_public_url(final_url)
            status = getattr(response, "status", 200)
            content_type = response.headers.get("Content-Type", "")
            if "text/html" not in content_type.lower() and "application/xhtml" not in content_type.lower():
                return PageEvidence(requested_url=url, final_url=final_url, status_code=status, error=f"Unsupported content type: {content_type or 'unknown'}")
            raw = response.read(config.max_bytes + 1)
            if len(raw) > config.max_bytes:
                return PageEvidence(requested_url=url, final_url=final_url, status_code=status, error=f"Response exceeded max_bytes={config.max_bytes}")
            html = _decode_body(raw, response.headers.get("Content-Encoding", ""), content_type)
            return parse_page(html, requested_url=url, final_url=final_url, status_code=status)
    except HTTPError as exc:
        return PageEvidence(requested_url=url, final_url=exc.geturl(), status_code=exc.code, error=str(exc))
    except (URLError, TimeoutError, UnsafeURLError, OSError) as exc:
        return PageEvidence(requested_url=url, final_url=url, status_code=0, error=str(exc))
