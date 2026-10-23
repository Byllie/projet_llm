"""Enregistre un profil et recommande les articles les plus proches."""

import argparse
import json

from psycopg2.extras import RealDictCursor

from db_manager import create_schema, db_connect
from embed_articles import EMBEDDING_DIM, EMBEDDING_MODEL, embed_texts


def create_profiles(conn):
    with conn.cursor() as cur:
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS profiles (
                username TEXT PRIMARY KEY,
                interests TEXT NOT NULL,
                embedding vector({EMBEDDING_DIM}) NOT NULL,
                embedding_model TEXT NOT NULL,
                updated_at TIMESTAMPTZ DEFAULT now()
            )
        """)
    conn.commit()


def save_profile(conn, username, interests):
    # Réutilise l'embedding si le profil n'a pas changé.
    with conn.cursor() as cur:
        cur.execute(
            "SELECT interests, embedding_model FROM profiles WHERE username = %s",
            (username,),
        )
        existing = cur.fetchone()
    if existing == (interests, EMBEDDING_MODEL):
        return
    embedding = embed_texts([interests])[0]
    vector = json.dumps(embedding)
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO profiles (username, interests, embedding, embedding_model)
            VALUES (%s, %s, %s::vector, %s)
            ON CONFLICT (username) DO UPDATE SET
                interests = EXCLUDED.interests,
                embedding = EXCLUDED.embedding,
                embedding_model = EXCLUDED.embedding_model,
                updated_at = now()
        """, (username, interests, vector, EMBEDDING_MODEL))
    conn.commit()


def recommendations(conn, username, limit):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT a.id, a.name, a.doi, a.authors, a.publication_date,
                   1 - (a.embedding <=> p.embedding) AS similarity
            FROM articles a CROSS JOIN profiles p
            WHERE p.username = %s AND a.embedding IS NOT NULL
            ORDER BY a.embedding <=> p.embedding, a.id
            LIMIT %s
        """, (username, limit))
        return cur.fetchall()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user", required=True, help="Identifiant du profil")
    parser.add_argument("--interests", help="Texte libre ; omettre pour réutiliser le profil")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    username = args.user.strip()
    if not username:
        parser.error("--user ne doit pas être vide")
    if args.limit < 1 or args.limit > 100:
        parser.error("--limit doit être compris entre 1 et 100")
    if args.interests is not None:
        args.interests = args.interests.strip()
        if not args.interests or len(args.interests) > 8000:
            parser.error("--interests doit contenir entre 1 et 8000 caractères")

    conn = db_connect()
    try:
        create_schema(conn, dim=EMBEDDING_DIM)
        create_profiles(conn)
        if args.interests is not None:
            save_profile(conn, username, args.interests)
        with conn.cursor() as cur:
            cur.execute("SELECT embedding_model FROM profiles WHERE username = %s", (username,))
            profile = cur.fetchone()
        if not profile:
            parser.error("Profil inconnu : ajoute --interests pour le créer")
        if profile[0] != EMBEDDING_MODEL:
            parser.error("Le modèle a changé : fournis --interests pour recalculer le profil")

        results = recommendations(conn, username, args.limit)
        print(f"\n{len(results)} recommandations pour {username} :")
        if not results:
            print("Aucun article avec embedding en base. Lance d'abord la collecte.")
        for rank, article in enumerate(results, 1):
            print(f"\n{rank}. {article['name']}")
            print(f"   Similarité cosinus : {article['similarity']:.4f}")
            print(f"   Auteurs : {', '.join(article['authors'] or [])}")
            print(f"   Date : {article['publication_date'] or 'inconnue'}")
            print(f"   DOI : {article['doi'] or 'non disponible'}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
