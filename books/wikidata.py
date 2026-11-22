"""Lauréats de prix littéraires via Wikidata SPARQL (4 dernières années).

Requête validée par l'auteur du projet : garde pour chaque (prix, année) la
meilleure combinaison lauréat + ouvrage disponible dans Wikidata.
"""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "letterbookd/0.1 (private book club)"

PRIZES = {
    "Q187300": "Prix Goncourt",
    "Q930356": "Prix Goncourt des Lycéens",
    "Q755723": "Prix Renaudot",
    "Q18945": "Prix Femina",
    "Q58352": "Prix Médicis",
    "Q1543399": "Prix Interallié",
    "Q1680241": "Prix Décembre",
    "Q1542826": "Grand prix du roman de l'Académie française",
    "Q3405825": "Prix du Livre Inter",
    "Q1320436": "Prix des Libraires",
    "Q952687": "Prix du roman Fnac",
}

_VALUES = " ".join(f"wd:{q}" for q in PRIZES)

QUERY = """
SELECT DISTINCT ?prix ?prixLabel ?annee ?laureat ?laureatLabel ?ouvrage ?ouvrageLabel WHERE {
  VALUES ?prix { %(V)s }
  {
    SELECT ?prix ?annee ?laureat ?ouvrage ?score WHERE {
      VALUES ?prix { %(V)s }
      {
        ?ouvrage p:P166 ?stmt .
        ?stmt ps:P166 ?prix ; pq:P585 ?date .
        BIND(YEAR(?date) AS ?annee)
        FILTER(?annee >= YEAR(NOW()) - 4)
        OPTIONAL { ?ouvrage wdt:P50 ?laureat . }
      }
      UNION
      {
        ?laureat p:P166 ?stmt .
        ?stmt ps:P166 ?prix ; pq:P585 ?date .
        ?laureat wdt:P31 wd:Q5 .
        BIND(YEAR(?date) AS ?annee)
        FILTER(?annee >= YEAR(NOW()) - 4)
        OPTIONAL { ?stmt pq:P1686 ?ouvrage . }
      }
      BIND((IF(BOUND(?laureat), 1, 0)) + (IF(BOUND(?ouvrage), 2, 0)) AS ?score)
    }
  }
  {
    SELECT ?prix ?annee (MAX(?score) AS ?scoreMax) WHERE {
      VALUES ?prix { %(V)s }
      {
        ?ouvrage p:P166 ?stmt .
        ?stmt ps:P166 ?prix ; pq:P585 ?date .
        BIND(YEAR(?date) AS ?annee)
        FILTER(?annee >= YEAR(NOW()) - 4)
        OPTIONAL { ?ouvrage wdt:P50 ?laureat . }
      }
      UNION
      {
        ?laureat p:P166 ?stmt .
        ?stmt ps:P166 ?prix ; pq:P585 ?date .
        ?laureat wdt:P31 wd:Q5 .
        BIND(YEAR(?date) AS ?annee)
        FILTER(?annee >= YEAR(NOW()) - 4)
        OPTIONAL { ?stmt pq:P1686 ?ouvrage . }
      }
      BIND((IF(BOUND(?laureat), 1, 0)) + (IF(BOUND(?ouvrage), 2, 0)) AS ?score)
    }
    GROUP BY ?prix ?annee
  }
  FILTER(?score = ?scoreMax)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en". }
}
ORDER BY ?prixLabel DESC(?annee)
""" % {"V": _VALUES}


def _qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1] if uri else ""


def fetch() -> list[dict]:
    url = f"{ENDPOINT}?{urlencode({'query': QUERY, 'format': 'json'})}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for b in data.get("results", {}).get("bindings", []):
        prize_qid = _qid(b.get("prix", {}).get("value", ""))
        work_qid = _qid(b.get("ouvrage", {}).get("value", ""))
        year = b.get("annee", {}).get("value")
        title = (b.get("ouvrageLabel", {}).get("value") or "").strip()
        author = (b.get("laureatLabel", {}).get("value") or "").strip()
        if not prize_qid or (not title and not author):
            continue
        # QID bruts filtrés quand labels manquants
        if title.startswith("Q") and title[1:].isdigit():
            title = ""
        if author.startswith("Q") and author[1:].isdigit():
            author = ""
        out.append({
            "prize_qid": prize_qid,
            "prize_name": b.get("prixLabel", {}).get("value") or PRIZES.get(prize_qid, prize_qid),
            "book_qid": work_qid or f"nowork:{prize_qid}:{year}:{author[:40]}",
            "title": title or f"— ({PRIZES.get(prize_qid, prize_qid)} {year})",
            "author": author,
            "year": int(year) if year and year.isdigit() else None,
        })
    return out
