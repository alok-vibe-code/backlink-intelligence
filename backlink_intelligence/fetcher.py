from __future__ import annotations

import gzip
import http.client
import io
import socket
import ssl
import zlib
from dataclasses import dataclass
from urllib import robotparser
from urllib.parse import urljoin, urlsplit, urlunsplit

from .html_utils import parse_page
from .models import PageEvidence
from .safety import ResolvedURL, UnsafeURLError, resolve_public_url


class FetchError(RuntimeError):
    """A bounded public fetch failed."""


class RobotsDeniedError(FetchError):
    """The publisher's robots policy does not permit this fetch."""


class UnsupportedContentError(FetchError):
    """The response is not supported by the evidence parser."""


@dataclass(slots=True)
class FetchConfig:
    connect_timeout: float = 5.0
    read_timeout: float = 12.0
    max_compressed_bytes: int = 1_000_000
    max_decompressed_bytes: int = 2_000_000
    max_redirects: int = 3
    max_paragraphs: int = 500
    max_headings: int = 200
    max_text_chars: int = 500_000
    respect_robots: bool = True
    user_agent: str = (
        "BacklinkIntelligence/1.1 (+https://github.com/alok-vibe-code/backlink-intelligence)"
    )

    @property
    def timeout(self) -> float:
        """Compatibility alias for callers that previously used one timeout."""

        return self.read_timeout

    @property
    def max_bytes(self) -> int:
        """Compatibility alias for the previous decompressed response limit."""

        return self.max_decompressed_bytes


@dataclass(frozen=True, slots=True)
class RawResponse:
    requested_url: str
    final_url: str
    status_code: int
    headers: dict[str, str]
    body: bytes


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, target: ResolvedURL, connect_ip: str, config: FetchConfig) -> None:
        super().__init__(target.hostname, target.port, timeout=config.connect_timeout)
        self._connect_ip = connect_ip
        self._connect_timeout = config.connect_timeout
        self._read_timeout = config.read_timeout

    def connect(self) -> None:
        self.sock = socket.create_connection(
            (self._connect_ip, self.port), timeout=self._connect_timeout
        )
        self.sock.settimeout(self._read_timeout)


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    def __init__(self, target: ResolvedURL, connect_ip: str, config: FetchConfig) -> None:
        super().__init__(
            target.hostname,
            target.port,
            timeout=config.connect_timeout,
            context=ssl.create_default_context(),
        )
        self._connect_ip = connect_ip
        self._connect_timeout = config.connect_timeout
        self._read_timeout = config.read_timeout
        self._server_hostname = target.hostname

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._connect_ip, self.port), timeout=self._connect_timeout
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket,
                server_hostname=self._server_hostname,
            )
        except Exception:
            raw_socket.close()
            raise
        self.sock.settimeout(self._read_timeout)


def _request_target(url: str) -> str:
    parsed = urlsplit(url)
    path = parsed.path or "/"
    return urlunsplit(("", "", path, parsed.query, ""))


def _read_limited(response: http.client.HTTPResponse, limit: int) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = response.read(min(65_536, limit + 1 - total))
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
        if total > limit:
            raise FetchError(f"Compressed response exceeded {limit} bytes.")
    return b"".join(chunks)


def _decompress_limited(raw: bytes, encoding: str, limit: int) -> bytes:
    encoding = encoding.lower().strip()
    if not encoding or encoding == "identity":
        if len(raw) > limit:
            raise FetchError(f"Response exceeded {limit} decompressed bytes.")
        return raw

    if encoding == "gzip":
        stream = gzip.GzipFile(fileobj=io.BytesIO(raw))
        try:
            output = stream.read(limit + 1)
        except (EOFError, OSError) as exc:
            raise FetchError("Invalid gzip response.") from exc
    elif encoding == "deflate":
        try:
            inflater = zlib.decompressobj()
            output = inflater.decompress(raw, limit + 1)
            if inflater.unconsumed_tail:
                raise FetchError(f"Response exceeded {limit} decompressed bytes.")
            remaining = limit + 1 - len(output)
            if remaining > 0:
                output += inflater.flush(remaining)
        except zlib.error as exc:
            raise FetchError("Invalid deflate response.") from exc
    else:
        raise UnsupportedContentError(f"Unsupported content encoding: {encoding}")

    if len(output) > limit:
        raise FetchError(f"Response exceeded {limit} decompressed bytes.")
    return output


def _host_header(target: ResolvedURL) -> str:
    default_port = 443 if target.scheme == "https" else 80
    host = f"[{target.hostname}]" if ":" in target.hostname else target.hostname
    return host if target.port == default_port else f"{host}:{target.port}"


def _request_once(url: str, config: FetchConfig, *, accept: str) -> RawResponse:
    target = resolve_public_url(url)
    if not target.addresses:
        raise UnsafeURLError("URL did not resolve to a public address.")

    last_error: Exception | None = None
    for connect_ip in target.addresses:
        connection: http.client.HTTPConnection
        if target.scheme == "https":
            connection = _PinnedHTTPSConnection(target, connect_ip, config)
        else:
            connection = _PinnedHTTPConnection(target, connect_ip, config)
        try:
            connection.request(
                "GET",
                _request_target(target.url),
                headers={
                    "Host": _host_header(target),
                    "User-Agent": config.user_agent,
                    "Accept": accept,
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "close",
                },
            )
            response = connection.getresponse()
            headers = {key.lower(): value for key, value in response.getheaders()}
            raw = _read_limited(response, config.max_compressed_bytes)
            body = _decompress_limited(
                raw,
                headers.get("content-encoding", ""),
                config.max_decompressed_bytes,
            )
            return RawResponse(
                requested_url=url,
                final_url=target.url,
                status_code=response.status,
                headers=headers,
                body=body,
            )
        except (OSError, TimeoutError, ssl.SSLError, http.client.HTTPException) as exc:
            last_error = exc
        finally:
            connection.close()
    raise FetchError("Remote host could not be reached securely.") from last_error


def _fetch_raw(url: str, config: FetchConfig, *, accept: str) -> RawResponse:
    requested_url = resolve_public_url(url).url
    current_url = requested_url
    for redirect_count in range(config.max_redirects + 1):
        response = _request_once(current_url, config, accept=accept)
        if response.status_code not in {301, 302, 303, 307, 308}:
            return RawResponse(
                requested_url=requested_url,
                final_url=response.final_url,
                status_code=response.status_code,
                headers=response.headers,
                body=response.body,
            )
        if redirect_count >= config.max_redirects:
            raise UnsafeURLError("Redirect limit exceeded.")
        location = response.headers.get("location", "").strip()
        if not location:
            raise FetchError("Redirect response did not include a location.")
        current_url = resolve_public_url(urljoin(current_url, location)).url
    raise UnsafeURLError("Redirect limit exceeded.")


def _decode_text(raw: bytes, content_type: str) -> str:
    charset = "utf-8"
    marker = "charset="
    if marker in content_type.lower():
        charset = content_type.lower().split(marker, 1)[1].split(";", 1)[0].strip() or "utf-8"
    try:
        return raw.decode(charset, errors="replace")
    except LookupError:
        return raw.decode("utf-8", errors="replace")


def _robots_allowed(url: str, config: FetchConfig) -> bool:
    parsed = urlsplit(url)
    robots_url = urlunsplit((parsed.scheme, parsed.netloc, "/robots.txt", "", ""))
    response = _fetch_raw(robots_url, config, accept="text/plain,*/*;q=0.1")
    if response.status_code in {401, 403}:
        raise RobotsDeniedError("Publisher robots policy denies automated access.")
    if response.status_code == 404:
        return True
    if response.status_code >= 500:
        raise RobotsDeniedError("Publisher robots policy is temporarily unavailable.")
    if response.status_code != 200:
        return True

    parser = robotparser.RobotFileParser()
    parser.set_url(response.final_url)
    parser.parse(_decode_text(response.body, response.headers.get("content-type", "")).splitlines())
    return parser.can_fetch(config.user_agent, url)


def fetch_page(url: str, config: FetchConfig | None = None) -> PageEvidence:
    config = config or FetchConfig()
    normalized = url
    try:
        normalized = resolve_public_url(url).url
        if config.respect_robots and not _robots_allowed(normalized, config):
            raise RobotsDeniedError("Publisher robots policy denies automated access.")
        response = _fetch_raw(
            normalized,
            config,
            accept="text/html,application/xhtml+xml;q=0.9,*/*;q=0.1",
        )
        content_type = response.headers.get("content-type", "")
        if response.status_code != 200:
            return PageEvidence(
                requested_url=normalized,
                final_url=response.final_url,
                status_code=response.status_code,
                error=f"Remote server returned HTTP {response.status_code}.",
            )
        if "text/html" not in content_type.lower() and "application/xhtml" not in content_type.lower():
            raise UnsupportedContentError(
                f"Unsupported content type: {content_type or 'unknown'}"
            )
        html = _decode_text(response.body, content_type)
        evidence = parse_page(
            html,
            requested_url=normalized,
            final_url=response.final_url,
            status_code=response.status_code,
        )
        evidence.paragraphs = evidence.paragraphs[: config.max_paragraphs]
        evidence.headings = evidence.headings[: config.max_headings]
        evidence.text = evidence.text[: config.max_text_chars]
        evidence.word_count = len(evidence.text.split())
        return evidence
    except (FetchError, RobotsDeniedError, UnsupportedContentError, UnsafeURLError) as exc:
        return PageEvidence(
            requested_url=normalized,
            final_url=normalized,
            status_code=0,
            error=f"{exc.__class__.__name__}: {exc}",
        )
