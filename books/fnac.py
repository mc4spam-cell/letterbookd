"""Scraper minimal des nouveautés livres sur fnac.com.

Pas de dépendance externe : HTMLParser stdlib. Parse les <article class="Article-itemGroup">
et extrait titre / auteur / couverture / résumé court.
"""
from __future__ import annotations

from html.parser import HTMLParser
from urllib.request import Request, urlopen

URL = "https://www.fnac.com/l726/Nouveautes-Livre"
UA = "Mozilla/5.0 (letterbookd/0.1 private book club)"


def _classes(attrs):
    for k, v in attrs:
        if k == "class" and v:
            return v.split()
    return []


class _FnacParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.items: list[dict] = []
        self._cur: dict | None = None
        self._buf: list[str] = []
        self._capture: str | None = None  # 'title' | 'author' | 'summary'

    def handle_starttag(self, tag, attrs):
        classes = _classes(attrs)
        if tag == "article" and "Article-itemGroup" in classes:
            self._cur = {"title": "", "author": "", "cover_url": "", "summary": "", "source_url": ""}
            return
        if self._cur is None:
            return
        if tag == "img" and "Article-itemVisualImg" in classes:
            attrd = dict(attrs)
            self._cur["cover_url"] = attrd.get("data-src") or attrd.get("src") or ""
        elif tag == "a" and not self._cur["source_url"]:
            href = dict(attrs).get("href", "")
            if href.startswith("/"):
                self._cur["source_url"] = "https://www.fnac.com" + href
            elif href.startswith("http"):
                self._cur["source_url"] = href
        elif tag == "p" and "Article-desc" in classes and "Article-descSub" not in classes:
            self._capture, self._buf = "title", []
        elif tag == "p" and "Article-descSub" in classes:
            self._capture, self._buf = "author", []
        elif tag == "p" and "moreInfos-summary" in classes:
            self._capture, self._buf = "summary", []

    def handle_data(self, data):
        if self._capture:
            self._buf.append(data)

    def handle_endtag(self, tag):
        if self._capture and tag == "p":
            self._cur[self._capture] = " ".join(self._buf).strip()
            self._capture, self._buf = None, []
        if tag == "article" and self._cur is not None:
            if self._cur["title"]:
                self.items.append(self._cur)
            self._cur = None


def fetch() -> list[dict]:
    req = Request(URL, headers={"User-Agent": UA, "Accept-Language": "fr"})
    with urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")
    p = _FnacParser()
    p.feed(html)
    return p.items
