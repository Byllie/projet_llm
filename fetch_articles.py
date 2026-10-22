#!/usr/bin/env python3

import os
import sys
import time

import requests

API_BASE = "https://api.openalex.org"
OPENALEX_API_KEY = os.environ.get("OPENALEX_API_KEY")

SELECT_FIELDS = ",".join(
    [
        "id",
        "doi",
        "display_name",
        "publication_date",
        "authorships",
        "primary_location",
        "abstract_inverted_index",
        "cited_by_count",
    ]
)

session = requests.Session()


def get(url, params):
    """GET avec retries"""
    params = {**params, "api_key": OPENALEX_API_KEY}
    for attempt in range(5):
        resp = session.get(url, params=params, timeout=30)
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (429, 500, 502, 503):
            wait = 2**attempt
            print(f"  HTTP {resp.status_code}, nouvelle tentative dans {wait}s", file=sys.stderr)
            time.sleep(wait)
            continue
        resp.raise_for_status()
    raise RuntimeError(f"Échec après 5 tentatives : {url}")


def resolve_topic(name):
    """Résout un nom de domaine/thème en topic OpenAlex."""
    data = get(f"{API_BASE}/topics", {"search": name, "per-page": 5})
    if not data["results"]:
        raise SystemExit(f"Aucun topic OpenAlex trouvé pour « {name} »")
    print("Topics correspondants :")
    for i, t in enumerate(data["results"]):
        print(f"  [{i}] {t['display_name']} (domaine : {t.get('domain', {}).get('display_name')})")
    topic = data["results"][0]
    print(f"Sélection : {topic['display_name']} ({topic['id']})")
    return topic


def fetch_works(topic_id, from_date, limit, work_type="article", sort="cited_by_count:desc"):
    """Récupère les works d'un topic, publiés depuis from_date, avec abstract.

    work_type : type de work OpenAlex ('article', 'preprint', 'dataset', ...).
    Par défaut 'article' pour exclure datasets et logiciels des dépôts .
    sort : critère de tri OpenAlex ('cited_by_count:desc', 'fwci:desc', ...).
    """
    works = []
    cursor = "*"
    params = {
        "filter": (
            f"topics.id:{topic_id},from_publication_date:{from_date},"
            f"has_abstract:true,type:{work_type}"
        ),
        "select": SELECT_FIELDS,
        "per-page": 200,
        "sort": sort,
    }
    while cursor and len(works) < limit:
        page = get(f"{API_BASE}/works", {**params, "cursor": cursor})
        results = page["results"]
        works.extend(results)
        print(f"  {len(works)} articles récupérés (total OpenAlex : {page['meta']['count']})")
        cursor = page["meta"].get("next_cursor")
        if len(results) == 0:
            break
    return works[:limit]


def rebuild_abstract(inverted_index):
    """Reconstruit l'abstract depuis l'index inversé d'OpenAlex."""
    if not inverted_index:
        return None
    positions = []
    for word, idxs in inverted_index.items():
        for idx in idxs:
            positions.append((idx, word))
    return " ".join(w for _, w in sorted(positions))


def to_article(w):
    """Extraction des champs utiles : nom, abstract, auteurs, journal."""
    return {
        "openalex_id": w["id"],
        "name": w["display_name"],
        "abstract": rebuild_abstract(w.get("abstract_inverted_index")),
        "authors": [a["author"]["display_name"] for a in w.get("authorships", [])],
        "journal": (w.get("primary_location") or {}).get("source", {}).get("display_name")
        if w.get("primary_location")
        else None,
        "doi": w["doi"],
        "publication_date": w["publication_date"],
        "cited_by_count": w["cited_by_count"],
    }


def fetch_topic_articles(topic_name, days, limit, work_type="article", sort="cited_by_count:desc"):
    """Pipeline de collecte : résout le topic et retourne les articles récents,
    triés par le critère OpenAlex demandé (défaut : citations décroissantes)."""
    topic = resolve_topic(topic_name)
    topic_id = topic["id"].rsplit("/", 1)[-1]
    from_date = time.strftime("%Y-%m-%d", time.gmtime(time.time() - days * 86400))
    print(f"Collecte des articles depuis le {from_date}...")
    works = fetch_works(topic_id, from_date, limit, work_type=work_type, sort=sort)
    articles = [to_article(w) for w in works]
    print(f"{len(articles)} articles collectés")
    return articles
