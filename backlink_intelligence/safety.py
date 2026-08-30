from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeURLError(RuntimeError):
    pass


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


def validate_public_url(url: str, *, resolve_dns: bool = True) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http:// and https:// URLs are supported.")
    if not parsed.hostname:
        raise UnsafeURLError("URL must include a hostname.")
    if parsed.username or parsed.password:
        raise UnsafeURLError("Credentials embedded in URLs are not allowed.")

    host = parsed.hostname.strip("[]").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise UnsafeURLError("Local/private hostnames are not allowed.")

    try:
        if not _is_public_ip(host):
            raise UnsafeURLError("Private, loopback, reserved, or link-local IPs are not allowed.")
        return url
    except ValueError:
        pass

    if resolve_dns:
        try:
            infos = socket.getaddrinfo(host, parsed.port or (443 if parsed.scheme == "https" else 80))
        except socket.gaierror as exc:
            raise UnsafeURLError(f"Hostname could not be resolved: {host}") from exc
        addresses = {info[4][0] for info in infos}
        if not addresses:
            raise UnsafeURLError(f"Hostname could not be resolved: {host}")
        for address in addresses:
            if not _is_public_ip(address):
                raise UnsafeURLError(
                    f"Hostname resolves to a non-public address ({address}); request blocked."
                )
    return url
