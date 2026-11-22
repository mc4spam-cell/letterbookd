"""Nouveautés livres via le flux RSS du Monde (rubrique Livres).

Format RSS 2.0 : items avec title, description, link, media:content@url.
Extrait, quand possible, le titre du livre (entre guillemets « ») et l'auteur
(après « de »). Sinon, garde l'intitulé d'origine.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.request import Request, urlopen

URL = "https://www.lemonde.fr/livres/rss_full.xml"
UA = "Mozilla/5.0 (letterbookd/0.1)"

MEDIA_NS = "{http://search.yahoo.com/mrss/}content"
# Pattern Le Monde Livres : « Titre », de Prénom Nom — pas toujours présent.
BOOK_AUTHOR_RE = re.compile(
    r"«[\s\xa0]*([^»]{2,200}?)[\s\xa0]*»[\s\xa0]*,?[\s\xa0]*(?:de|d')[\s\xa0]+"
    r"([A-ZÀ-Ö][\wÀ-ÿ\-']+(?:[\s\xa0]+[A-ZÀ-Ö][\wÀ-ÿ\-']+){0,3})"
)


def _parse_item(title: str) -> tuple[str, str]:
    """Si la forme « X », de Y est là, extrait X et Y ; sinon garde le titre complet."""
    m = BOOK_AUTHOR_RE.search(title)
    if m:
        return m.group(1).strip()[:500], m.group(2).strip()[:300]
    return title.strip()[:500], ""


def fetch() -> list[dict]:
    req = Request(URL, headers={"User-Agent": UA, "Accept": "application/rss+xml,application/xml"})
    with urlopen(req, timeout=30) as resp:
        xml_bytes = resp.read()
    root = ET.fromstring(xml_bytes)
    out = []
    for item in root.findall(".//item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        link_el = item.find("link")
        media = item.find(MEDIA_NS)
        full_title = (title_el.text or "").strip() if title_el is not None else ""
        if not full_title:
            continue
        description = (desc_el.text or "").strip() if desc_el is not None else ""
        link = (link_el.text or "").strip() if link_el is not None else ""
        cover = media.attrib.get("url", "") if media is not None else ""
        book, author = _parse_item(full_title)
        out.append({
            "title": book,
            "author": author,
            "summary": description,
            "cover_url": cover,
            "source_url": link,
        })
    return out
