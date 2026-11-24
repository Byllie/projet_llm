#!/usr/bin/env python3
"""Opérations base de données : connexion, schémas (articles, profiles), requêtes."""

import json
import os

import psycopg2
from psycopg2.extras import RealDictCursor


def db_connect():
    return psycopg2.connect(
        host=os.environ.get("PGHOST", "localhost"),
        port=os.environ.get("PGPORT", "5432"),
        user=os.environ.get("PGUSER", "scholar"),
        password=os.environ.get("PGPASSWORD", "scholar"),
        dbname=os.environ.get("PGDATABASE", "scholar"),
    )


def create_schema(conn, dim=1536):
    """Crée l'extension vector et la table articles si nécessaire."""
    with conn.cursor() as cur:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS articles (
                id               SERIAL PRIMARY KEY,
                openalex_id      TEXT UNIQUE NOT NULL,
                name             TEXT NOT NULL,
                abstract         TEXT,
                authors          JSONB,
                journal          TEXT,
                doi              TEXT,
                publication_date TEXT,
                cited_by_count   INTEGER,
                embedding        vector({dim}),
                fetched_at       TIMESTAMPTZ DEFAULT now()
            );
            """
        )
    conn.commit()


def insert_articles(conn, articles, embeddings):
    """Insère (ou met à jour) les articles avec leur embedding."""
    inserted = 0
    with conn.cursor() as cur:
        for art, emb in zip(articles, embeddings):
            cur.execute(
                """
                INSERT INTO articles (openalex_id, name, abstract, authors, journal,
                                      doi, publication_date, cited_by_count, embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector)
                ON CONFLICT (openalex_id) DO UPDATE SET
                    name = EXCLUDED.name,
                    abstract = EXCLUDED.abstract,
                    authors = EXCLUDED.authors,
                    journal = EXCLUDED.journal,
                    cited_by_count = EXCLUDED.cited_by_count,
                    embedding = EXCLUDED.embedding,
                    fetched_at = now();
                """,
                (
                    art["openalex_id"],
                    art["name"],
                    art["abstract"],
                    json.dumps(art["authors"]),
                    art["journal"],
                    art["doi"],
                    art["publication_date"],
                    art["cited_by_count"],
                    "[" + ",".join(f"{x:.6f}" for x in emb) + "]",
                ),
            )
            inserted += 1
    conn.commit()
    return inserted


def create_profiles_table(conn, dim=1536):
    """Crée la table profiles (un chercheur, ses intérêts et leur embedding)."""
    with conn.cursor() as cur:
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS profiles (
                username        TEXT PRIMARY KEY,
                interests      TEXT NOT NULL,
                embedding      vector({dim}) NOT NULL,
                embedding_model TEXT NOT NULL,
                updated_at     TIMESTAMPTZ DEFAULT now()
            );
            """
        )
    conn.commit()


def get_profile(conn, username):
    """Retourne (interests, embedding_model) du profil, ou None s'il n'existe pas."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT interests, embedding_model FROM profiles WHERE username = %s",
            (username,),
        )
        return cur.fetchone()


def upsert_profile(conn, username, interests, embedding, model):
    """Insère ou met à jour un profil avec son embedding."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO profiles (username, interests, embedding, embedding_model)
            VALUES (%s, %s, %s::vector, %s)
            ON CONFLICT (username) DO UPDATE SET
                interests = EXCLUDED.interests,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                updated_at = now();
            """,
            (username, interests, json.dumps(embedding), model),
        )
    conn.commit()


def find_top_articles(conn, username, limit):
    """Top-K des articles les plus proches du profil, par similarité cosinus."""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT a.id, a.openalex_id, a.name, a.abstract, a.doi, a.authors,
                   a.publication_date, 1 - (a.embedding <=> p.embedding) AS similarity
            FROM articles a
            JOIN (SELECT embedding FROM profiles WHERE username = %s) AS p ON true
            WHERE a.embedding IS NOT NULL
            ORDER BY a.embedding <=> p.embedding, a.id
            LIMIT %s
            """,
            (username, limit),
        )
        return cur.fetchall()


def create_clicks_table(conn):
    """Crée la table clicks (journal des clics sur les liens trackés)."""
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS clicks (
                id         SERIAL PRIMARY KEY,
                username   TEXT NOT NULL,
                article_id INTEGER NOT NULL REFERENCES articles(id),
                clicked_at TIMESTAMPTZ DEFAULT now()
            );
            """
        )
    conn.commit()


def log_click(conn, username, article_id):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO clicks (username, article_id) VALUES (%s, %s)",
            (username, article_id),
        )
    conn.commit()


def parse_vector(s):
    """Convertit la représentation texte pgvector '[0.1,0.2,...]' en liste de floats."""
    return [float(x) for x in s.strip("[]").split(",")]


def vector_to_text(v):
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def get_article(conn, article_id):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, openalex_id, name, doi, authors, publication_date
            FROM articles WHERE id = %s
            """,
            (article_id,),
        )
        return cur.fetchone()


def update_profile_embedding(conn, username, article_id, weight=0.1):
    """Fait dériver l'embedding du profil vers celui de l'article cliqué.

    new = normalise((1 - weight) * profil + weight * article)  — le profil
    garde weight de chaque article lu, l'historique des clics s'accumule.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT embedding::text FROM articles WHERE id = %s", (article_id,))
        row = cur.fetchone()
        if not row:
            return False
        article_emb = parse_vector(row[0])
        cur.execute("SELECT embedding::text FROM profiles WHERE username = %s", (username,))
        row = cur.fetchone()
        if not row:
            return False
        profile_emb = parse_vector(row[0])

    mixed = [(1 - weight) * p + weight * a for p, a in zip(profile_emb, article_emb)]
    norm = sum(x * x for x in mixed) ** 0.5
    if norm > 0:
        mixed = [x / norm for x in mixed]

    with conn.cursor() as cur:
        cur.execute(
            "UPDATE profiles SET embedding = %s::vector, updated_at = now() WHERE username = %s",
            (vector_to_text(mixed), username),
        )
    conn.commit()
    return True


if __name__ == "__main__":
    conn = db_connect()
    try:
        create_schema(conn)
        create_profiles_table(conn)
        print("Schéma créé (extension vector + tables articles et profiles).")
    finally:
        conn.close()
