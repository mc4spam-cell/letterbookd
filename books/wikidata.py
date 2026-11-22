"""Lauréats de prix littéraires via Wikidata SPARQL (depuis 2020)."""
from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ENDPOINT = "https://query.wikidata.org/sparql"
UA = "letterbookd/0.1 (private book club)"

# Prix suivis. Le label est écrasé par celui renvoyé par Wikidata si dispo.
PRIZES = {
    "Q191113": "Prix Goncourt",
    "Q1056607": "Prix Renaudot",
    "Q1265837": "Prix Femina",
    "Q1077979": "Prix Médicis",
    "Q3400048": "Prix Interallié",
}

QUERY = """
SELECT ?prize ?prizeLabel ?livre ?livreLabel ?auteurLabel ?annee WHERE {
  VALUES ?prize { %s }
  ?livre wdt:P166 ?prize .
  OPTIONAL { ?livre wdt:P50 ?auteur . }
  OPTIONAL { ?livre wdt:P577 ?date . BIND(YEAR(?date) AS ?annee) }
  FILTER(?annee >= 2020)
  SERVICE wikibase:label { bd:serviceParam wikibase:language "fr,en" }
}
"""


def fetch() -> list[dict]:
    q = QUERY % " ".join(f"wd:{qid}" for qid in PRIZES)
    url = f"{ENDPOINT}?{urlencode({'query': q, 'format': 'json'})}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"})
    with urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = []
    for b in data.get("results", {}).get("bindings", []):
        prize_uri = b.get("prize", {}).get("value", "")
        prize_qid = prize_uri.rsplit("/", 1)[-1]
        book_uri = b.get("livre", {}).get("value", "")
        book_qid = book_uri.rsplit("/", 1)[-1]
        year = b.get("annee", {}).get("value")
        out.append({
            "prize_qid": prize_qid,
            "prize_name": b.get("prizeLabel", {}).get("value") or PRIZES.get(prize_qid, prize_qid),
            "book_qid": book_qid,
            "title": b.get("livreLabel", {}).get("value", "").strip(),
            "author": b.get("auteurLabel", {}).get("value", "").strip(),
            "year": int(year) if year and year.isdigit() else None,
        })
    return out
