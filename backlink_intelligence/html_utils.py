from __future__ import annotations

import re
from html.parser import HTMLParser
from urllib.parse import urljoin

from .models import PageEvidence, PageLink

_WS = re.compile(r"\s+")


def clean_text(value: str) -> str:
    return _WS.sub(" ", value or "").strip()


class EvidenceHTMLParser(HTMLParser):
    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.title_parts: list[str] = []
        self.h1_parts: list[str] = []
        self.headings: list[str] = []
        self.paragraphs: list[str] = []
        self.links: list[PageLink] = []
        self.canonical = ""
        self.robots: list[str] = []
        self._stack: list[str] = []
        self._title_depth = 0
        self._h1_depth = 0
        self._heading_tag: str | None = None
        self._heading_parts: list[str] = []
        self._paragraph_depth = 0
        self._paragraph_parts: list[str] = []
        self._current_link: dict | None = None
        self._skip_depth = 0
        self._landmark_stack: list[str] = []

    def _placement(self) -> str:
        landmarks = set(self._landmark_stack)
        if "footer" in landmarks:
            return "footer"
        if "nav" in landmarks:
            return "navigation"
        if "aside" in landmarks:
            return "sidebar"
        if "header" in landmarks:
            return "navigation"
        if "article" in landmarks or "main" in landmarks:
            return "editorial_context"
        return "unknown"

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attrs_dict = {k.lower(): (v or "") for k, v in attrs}
        self._stack.append(tag)
        if tag in {"script", "style", "noscript", "template", "svg"}:
            self._skip_depth += 1
        if tag in {"article", "main", "nav", "aside", "footer", "header"}:
            self._landmark_stack.append(tag)
        if tag == "title":
            self._title_depth += 1
        if tag == "h1":
            self._h1_depth += 1
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._heading_tag = tag
            self._heading_parts = []
        if tag == "p":
            self._paragraph_depth += 1
            if self._paragraph_depth == 1:
                self._paragraph_parts = []
        if tag == "link" and attrs_dict.get("rel", "").lower() == "canonical":
            href = clean_text(attrs_dict.get("href", ""))
            if href:
                self.canonical = urljoin(self.base_url, href)
        if tag == "meta" and attrs_dict.get("name", "").lower() in {"robots", "googlebot"}:
            for item in attrs_dict.get("content", "").lower().split(","):
                item = clean_text(item)
                if item and item not in self.robots:
                    self.robots.append(item)
        if tag == "a":
            href = clean_text(attrs_dict.get("href", ""))
            rel = tuple(sorted({v.lower() for v in attrs_dict.get("rel", "").split() if v}))
            self._current_link = {"href": urljoin(self.base_url, href) if href else "", "text": [], "rel": rel, "placement": self._placement()}

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title" and self._title_depth:
            self._title_depth -= 1
        if tag == "h1" and self._h1_depth:
            self._h1_depth -= 1
        if self._heading_tag == tag:
            text = clean_text(" ".join(self._heading_parts))
            if text:
                self.headings.append(text)
            self._heading_tag = None
            self._heading_parts = []
        if tag == "p" and self._paragraph_depth:
            self._paragraph_depth -= 1
            if self._paragraph_depth == 0:
                text = clean_text(" ".join(self._paragraph_parts))
                if text:
                    self.paragraphs.append(text)
                self._paragraph_parts = []
        if tag == "a" and self._current_link is not None:
            text = clean_text(" ".join(self._current_link["text"]))
            paragraph = clean_text(" ".join(self._paragraph_parts)) if self._paragraph_parts else ""
            href = self._current_link["href"]
            if href:
                self.links.append(PageLink(href=href, text=text, rel=self._current_link["rel"], context=paragraph, paragraph=paragraph, placement=self._current_link["placement"]))
            self._current_link = None
        if tag in {"script", "style", "noscript", "template", "svg"} and self._skip_depth:
            self._skip_depth -= 1
        if tag in {"article", "main", "nav", "aside", "footer", "header"}:
            for i in range(len(self._landmark_stack) - 1, -1, -1):
                if self._landmark_stack[i] == tag:
                    del self._landmark_stack[i]
                    break
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = clean_text(data)
        if not text:
            return
        if self._title_depth:
            self.title_parts.append(text)
        if self._h1_depth:
            self.h1_parts.append(text)
        if self._heading_tag:
            self._heading_parts.append(text)
        if self._paragraph_depth:
            self._paragraph_parts.append(text)
        if self._current_link is not None:
            self._current_link["text"].append(text)


def parse_page(html: str, *, requested_url: str, final_url: str, status_code: int) -> PageEvidence:
    parser = EvidenceHTMLParser(final_url)
    parser.feed(html)
    title = clean_text(" ".join(parser.title_parts))
    h1 = clean_text(" ".join(parser.h1_parts))
    paragraphs = [p for p in parser.paragraphs if len(p.split()) >= 3]
    text = clean_text(" ".join([title, h1, *parser.headings, *paragraphs]))
    return PageEvidence(requested_url=requested_url, final_url=final_url, status_code=status_code, title=title, h1=h1, canonical=parser.canonical, robots=tuple(parser.robots), text=text, paragraphs=paragraphs, headings=parser.headings, links=parser.links, word_count=len(text.split()))
