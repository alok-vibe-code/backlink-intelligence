from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit


class UnsafeURLError(RuntimeError):
    """Raised when a URL cannot be fetched without crossing a trust boundary."""


@dataclass(frozen=True, slots=True)
class ResolvedURL:
    """A normalized public URL and the public IPs approved for one connection."""

    url: str
    scheme: str
    hostname: str
    port: int
    addresses: tuple[str, ...]


def _is_public_ip(value: str) -> bool:
    ip = ipaddress.ip_address(value)
    return not (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    )


def _normalized_parts(url: str) -> tuple[SplitResult, str, int, str]:
    if not isinstance(url, str) or not url.strip():
        raise UnsafeURLError("URL is required.")
    if len(url) > 2048:
        raise UnsafeURLError("URL exceeds the 2048 character limit.")

    try:
        parsed = urlsplit(url.strip())
        port = parsed.port
    except ValueError as exc:
        raise UnsafeURLError("URL contains an invalid port or hostname.") from exc

    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http:// and https:// URLs are supported.")
    if not parsed.hostname:
        raise UnsafeURLError("URL must include a hostname.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("Credentials embedded in URLs are not allowed.")

    try:
        hostname = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise UnsafeURLError("URL hostname is not valid IDNA.") from exc
    if hostname in {"localhost", "localhost.localdomain"} or hostname.endswith(".local"):
        raise UnsafeURLError("Local/private hostnames are not allowed.")

    default_port = 443 if scheme == "https" else 80
    port = port or default_port
    if port not in {80, 443}:
        raise UnsafeURLError("Only ports 80 and 443 are supported.")

    host_for_url = f"[{hostname}]" if ":" in hostname else hostname
    netloc = host_for_url
    if port != default_port:
        netloc = f"{host_for_url}:{port}"
    path = parsed.path or "/"
    normalized = urlunsplit((scheme, netloc, path, parsed.query, ""))
    return parsed, hostname, port, normalized


def resolve_public_url(url: str, *, resolve_dns: bool = True) -> ResolvedURL:
    """Normalize a URL and resolve every address before a connection is attempted."""

    _, hostname, port, normalized = _normalized_parts(url)
    addresses: set[str] = set()

    try:
        literal = ipaddress.ip_address(hostname)
    except ValueError:
        literal = None

    if literal is not None:
        if not _is_public_ip(hostname):
            raise UnsafeURLError("Private, loopback, reserved, or link-local IPs are not allowed.")
        addresses.add(str(literal))
    elif resolve_dns:
        try:
            infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise UnsafeURLError(f"Hostname could not be resolved: {hostname}") from exc
        addresses = {info[4][0] for info in infos}
        if not addresses:
            raise UnsafeURLError(f"Hostname could not be resolved: {hostname}")
        for address in addresses:
            try:
                public = _is_public_ip(address)
            except ValueError as exc:
                raise UnsafeURLError("Hostname resolved to an invalid address.") from exc
            if not public:
                raise UnsafeURLError(
                    f"Hostname resolves to a non-public address ({address}); request blocked."
                )

    scheme = urlsplit(normalized).scheme
    return ResolvedURL(
        url=normalized,
        scheme=scheme,
        hostname=hostname,
        port=port,
        addresses=tuple(sorted(addresses)),
    )


def validate_public_url(url: str, *, resolve_dns: bool = True) -> str:
    """Compatibility wrapper returning the normalized, validated URL."""

    return resolve_public_url(url, resolve_dns=resolve_dns).url
