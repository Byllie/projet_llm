#!/usr/bin/env python3

import os

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-small"  # 1536 dimensions
EMBEDDING_DIM = 1536
EMBED_BATCH_SIZE = 100


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
