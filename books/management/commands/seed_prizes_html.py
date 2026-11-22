"""Alimentation ponctuelle depuis un export HTML Wikidata Query Service.

Utile quand l'endpoint SPARQL est indisponible. Parse le tableau rendu par
query.wikidata.org et nourrit PrizeWinner en réutilisant la même logique
d'enregistrement + enrichissement Open Library que fetch_prizes.
"""
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from books.management.commands.fetch_prizes import persist

ROW_RE = re.compile(r'<tr data-index="\d+">(.*?)</tr>', re.S)
CELL_RE = re.compile(r'<td[^>]*>(.*?)</td>', re.S)
QID_RE = re.compile(r'entity/(Q\d+)')
# Labels : <span title=": VALUE@fr">TEXT</span> ou <span title=": VALUE">TEXT</span>
LABEL_RE = re.compile(r'<span title=":\s*([^"]*?)(?:@[a-z-]+)?"[^>]*>([^<]*)</span>')


def _qid(html: str) -> str:
    m = QID_RE.search(html)
    return m.group(1) if m else ""


def _label(html: str) -> str:
    m = LABEL_RE.search(html)
    return (m.group(2) if m else "").strip()


def parse_html(path: Path) -> list[dict]:
    html = path.read_text(encoding="utf-8", errors="replace")
    rows = []
    for row_html in ROW_RE.findall(html):
        cells = CELL_RE.findall(row_html)
        if len(cells) < 7:
            continue
        prize_qid = _qid(cells[0])
        prize_label = _label(cells[1])
        year_s = _label(cells[2])
        laureat_qid = _qid(cells[3])
        laureat_label = _label(cells[4])
        ouvrage_qid = _qid(cells[5])
        ouvrage_label = _label(cells[6])
        title = ouvrage_label
        author = laureat_label
        # Si le QID 'ouvrage' est en fait la personne (P166 posé sur l'auteur),
        # permute : auteur = ouvrageLabel, titre = vide.
        if not author and title:
            author, title = title, ""
            if ouvrage_qid and not laureat_qid:
                laureat_qid, ouvrage_qid = ouvrage_qid, ""
        if not prize_qid or (not title and not author):
            continue
        key = ouvrage_qid or f"nowork:{laureat_qid or author[:40]}:{prize_qid}:{year_s}"
        rows.append({
            "prize_qid": prize_qid,
            "prize_name": prize_label or prize_qid,
            "book_qid": key,
            "title": title,
            "author": author,
            "year": int(year_s) if year_s.isdigit() else None,
        })
    return rows


class Command(BaseCommand):
    help = "Nourrit PrizeWinner depuis un export HTML Wikidata Query Service."

    def add_arguments(self, parser):
        parser.add_argument("path", help="Chemin vers le fichier .html")

    def handle(self, path, **o):
        rows = parse_html(Path(path))
        self.stdout.write(f"html: {len(rows)} lignes parsées")
        persist(rows, self.stdout)
