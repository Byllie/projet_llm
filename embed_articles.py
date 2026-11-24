#!/usr/bin/env python3

import json
import os

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
EMBEDDING_DIM = 1536
EMBED_BATCH_SIZE = 100
CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")


def embed_texts(texts, session=None):
    """Vectorise une liste de textes via l'API OpenAI, par lots."""
    if not OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY manquante : définissez la variable d'environnement.")
    http = session or requests.Session()
    embeddings = []
    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        resp = http.post(
            OPENAI_EMBEDDINGS_URL,
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={"model": EMBEDDING_MODEL, "input": batch},
            timeout=60,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Erreur OpenAI {resp.status_code} : {resp.text[:200]}")
        data = resp.json()["data"]
        data.sort(key=lambda d: d["index"])
        embeddings.extend(d["embedding"] for d in data)
        print(f"  {min(i + EMBED_BATCH_SIZE, len(texts))}/{len(texts)} textes embeddés")
    return embeddings


def article_text(article):
    """Texte passé à l'embedding : titre + abstract (tronqué à ~8000 caractères)."""
    text = f"{article['name']}\n\n{article['abstract'] or ''}"
    return text[:8000]


def embed_articles(articles):
    """Vectorise une liste d'articles et retourne les embeddings dans le même ordre."""
    print(f"Embeddings via OpenAI ({EMBEDDING_MODEL})...")
    return embed_texts([article_text(a) for a in articles])


def extract_search_terms(interests, clicked_titles=None):
    """Transforme les intérêts libres en requête de recherche anglaise.

    La littérature scientifique est majoritairement en anglais : on demande
    au LLM une requête courte et directe pour OpenAlex.

    S'il y a des clics récents, la requête s'adapte à la dérive : le LLM
    tient compte à la fois de l'intérêt déclaré et des lectures réelles —
    c'est l'envie actuelle du chercheur, pas seulement l'initiale.
    """
    if not OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY manquante : définissez la variable d'environnement.")
    if clicked_titles:
        lus = "\n".join(f"- {t}" for t in clicked_titles)
        contenu = (
            f"Intérêts déclarés du chercheur : « {interests} »\n\n"
            f"Articles qu'il a réellement lus récemment :\n{lus}\n\n"
            "Synthétise la requête de recherche anglaise (3 à 8 mots-clés) qui reflète "
            "ses intérêts ACTUELS : garde l'intérêt de base mais intègre les thèmes "
            "qu'il lit vraiment. "
            'Réponds en JSON : {"requete": "..."}'
        )
    else:
        contenu = (
            "Traduis ces intérêts scientifiques en une requête de recherche "
            f"en anglais (3 à 6 mots, mots-clés scientifiques) : « {interests} ». "
            'Réponds en JSON : {"requete": "..."}'
        )
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": CHAT_MODEL,
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": contenu}],
        },
        timeout=60,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur OpenAI {resp.status_code} : {resp.text[:200]}")
    return json.loads(resp.json()["choices"][0]["message"]["content"])["requete"]


def generate_interests(author, works):
    """Rédige le texte d'intérêts d'un chercheur à partir de son profil ORCID.

    author : objet auteur OpenAlex (topics, affiliation, compteurs).
    works :[{titre, date, citations}] — ses travaux les plus cités.
    """
    if not OPENAI_API_KEY:
        raise SystemExit("OPENAI_API_KEY manquante : définissez la variable d'environnement.")
    topics = ", ".join(t["display_name"] for t in (author.get("topics") or [])[:6])
    affiliation = ", ".join(
        a["institution"]["display_name"] for a in (author.get("affiliations") or [])[:2]
    )
    liste = "\n".join(f"- {w['titre']} ({w['date']}, {w['citations']} citations)" for w in works)
    resp = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": CHAT_MODEL,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"Profil OpenAlex du chercheur {author.get('display_name')} : \n"
                        f"Thèmes : {topics or 'inconnus'}\n"
                        f"Affiliations : {affiliation or 'inconnues'}\n"
                        f"Nombre de travaux : {author.get('works_count')}\n\n"
                        f"Ses travaux les plus cités :\n{liste or 'inconnus'}\n\n"
                        "Rédige en 2 à 4 phrases, en français, ses intérêts de recherche "
                        "tels qu'il les décrirait lui-même pour un service de veille "
                        "scientifique (domaines, méthodes, themes récurrents). "
                        'Réponds en JSON : {"interets": "..."}'
                    ),
                }
            ],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur OpenAI {resp.status_code} : {resp.text[:200]}")
    return json.loads(resp.json()["choices"][0]["message"]["content"])["interets"]
