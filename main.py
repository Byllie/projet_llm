#!/usr/bin/env python3
"""

Usage :
    python3 main.py --topic "machine learning" --days 7 --limit 50
    python3 main.py --topic "machine learning" --out articles.json
"""

import argparse
import json

from bd import create_schema, db_connect, insert_articles
from embed_articles import EMBEDDING_DIM, embed_articles
from fetch_articles import fetch_topic_articles


def main():
    parser = argparse.ArgumentParser(description="Collecte OpenAlex -> embeddings OpenAI -> pgvector")
    parser.add_argument("--topic", required=True, help="Domaine/thème (ex : 'machine learning')")
    parser.add_argument("--days", type=int, default=7, help="Articles publiés depuis N jours (défaut : 7)")
    parser.add_argument("--limit", type=int, default=50, help="Nombre max d'articles (défaut : 50)")
    parser.add_argument("--type", default="article", help="Type de work OpenAlex (défaut : article)")
    parser.add_argument("--out", default=None, help="Export JSON optionnel des articles")
    args = parser.parse_args()

    articles = fetch_topic_articles(args.topic, args.days, args.limit, work_type=args.type)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(articles, f, ensure_ascii=False, indent=2)
        print(f"Export JSON : {args.out}")

    embeddings = embed_articles(articles)

    print("Export vers PostgreSQL/pgvector...")
    conn = db_connect()
    try:
        create_schema(conn, dim=EMBEDDING_DIM)
        inserted = insert_articles(conn, articles, embeddings)
        print(f"{inserted} articles insérés dans la table articles.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
