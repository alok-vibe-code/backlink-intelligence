from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from .models import BacklinkEvidence, OutboundEvidence, PageEvidence


def normalize_url(url: str) -> str:
    p = urlparse(url)
    scheme = (p.scheme or "https").lower()
    host = (p.hostname or "").lower()
    port = p.port
    netloc = host
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        netloc = f"{host}:{port}"
    path = p.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunparse((scheme, netloc, path, "", p.query, ""))


def same_destination(a: str, b: str) -> bool:
    try:
        return normalize_url(a) == normalize_url(b)
    except ValueError:
        return False


def find_backlink(source: PageEvidence, target_url: str) -> BacklinkEvidence:
    for link in source.links:
        if same_destination(link.href, target_url):
            return BacklinkEvidence(found=True, source_url=source.final_url, target_url=target_url, anchor=link.text, rel=link.rel, context=link.context, paragraph=link.paragraph, placement=link.placement)
    return BacklinkEvidence(found=False, source_url=source.final_url, target_url=target_url)


def outbound_evidence(page: PageEvidence) -> OutboundEvidence:
    source_host = (urlparse(page.final_url).hostname or "").lower()
    external = []
    for link in page.links:
        host = (urlparse(link.href).hostname or "").lower()
        if host and host != source_host and not host.endswith("." + source_host):
            external.append(link)
    domains = {(urlparse(l.href).hostname or "").lower() for l in external}
    nofollow = sum("nofollow" in l.rel for l in external)
    sponsored = sum("sponsored" in l.rel for l in external)
    ugc = sum("ugc" in l.rel for l in external)
    follow = len(external) - nofollow
    density = (len(external) / max(page.word_count, 1)) * 1000
    flags: list[str] = []
    if page.word_count and density > 45:
        flags.append("high_external_link_density")
    if len(domains) >= 35:
        flags.append("many_unique_external_domains")
    if len(external) >= 40 and sponsored == 0 and nofollow / max(len(external), 1) < 0.1:
        flags.append("many_followed_external_links")
    return OutboundEvidence(total_links=len(page.links), external_links=len(external), unique_external_domains=len(domains), external_links_per_1000_words=round(density, 2), follow_links=follow, nofollow_links=nofollow, sponsored_links=sponsored, ugc_links=ugc, review_flags=flags)
