"""Enregistre un profil et recommande les articles les plus proches."""

import argparse

from bd import create_profiles_table, create_schema, db_connect, find_top_articles, get_profile, upsert_profile
from embed_articles import EMBEDDING_DIM, EMBEDDING_MODEL, embed_texts


def save_profile(conn, username, interests):
    """Enregistre le profil ; réutilise l'embedding si rien n'a changé."""
    existing = get_profile(conn, username)
    if existing == (interests, EMBEDDING_MODEL):
        return
    embedding = embed_texts([interests])[0]
    upsert_profile(conn, username, interests, embedding, EMBEDDING_MODEL)


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
        create_profiles_table(conn, dim=EMBEDDING_DIM)
        if args.interests is not None:
            save_profile(conn, username, args.interests)

        profile = get_profile(conn, username)
        if not profile:
            parser.error("Profil inconnu : ajoute --interests pour le créer")
        if profile[1] != EMBEDDING_MODEL:
            parser.error("Le modèle a changé : fournis --interests pour recalculer le profil")

        results = find_top_articles(conn, username, args.limit)
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
