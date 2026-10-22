#!/usr/bin/env python3

import json
import os

import psycopg2


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


if __name__ == "__main__":
    conn = db_connect()
    try:
        create_schema(conn)
        print("Schéma créé (extension vector + table articles).")
    finally:
        conn.close()
