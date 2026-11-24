"""API FastAPI : profils chercheurs, recommandations, newsletter, liens trackés.

Lancement : uvicorn api:app --host 0.0.0.0 --port 8000
"""

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel, Field

from bd import (
    create_clicks_table,
    create_profiles_table,
    create_schema,
    create_sent_articles_table,
    db_connect,
    find_top_articles,
    get_article,
    get_profile,
    get_recent_clicked,
    insert_articles,
    log_click,
    record_recommended,
    update_profile_embedding,
    upsert_profile,
)
from embed_articles import (
    EMBEDDING_DIM,
    EMBEDDING_MODEL,
    embed_articles,
    embed_texts,
    extract_search_terms,
    generate_interests,
)
from fetch_articles import extract_orcid, fetch_author, fetch_author_works, search_articles
from newsletter_gen import build_newsletter_html, generate_content, short_id
from tracker import make_token, read_token

EMBEDDING_WEIGHT = 0.1  # part de l'article cliqué dans le profil mis à jour
BASE_URL = os.environ.get("APP_BASE_URL", "http://localhost:8000")


@asynccontextmanager
async def lifespan(app):
    conn = db_connect()
    try:
        create_schema(conn, dim=EMBEDDING_DIM)
        create_profiles_table(conn, dim=EMBEDDING_DIM)
        create_clicks_table(conn)
        create_sent_articles_table(conn)
    finally:
        conn.close()
    yield


app = FastAPI(title="Scholar Digest", lifespan=lifespan)


class ProfileIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    interests: str | None = Field(default=None, max_length=8000)
    orcid: str | None = Field(default=None, max_length=64)


def article_url(art):
    return art["doi"] or art["openalex_id"]


@app.post("/profiles")
def create_profile(body: ProfileIn):
    """Crée ou met à jour un profil et retourne son top 10.

    Fournir soit `interests` (texte libre), soit `orcid` (lien ou identifiant) :
    dans ce cas le LLM rédige les intérêts à partir du profil OpenAlex
    du chercheur et de ses travaux.
    """
    if not body.interests and not body.orcid:
        raise HTTPException(422, "Fournir interests ou orcid")

    orcid_nom = None
    if body.interests is None:
        orcid = extract_orcid(body.orcid)
        if not orcid:
            raise HTTPException(422, "ORCID invalide (attendu : 0000-0000-0000-0000 ou lien orcid.org)")
        author = fetch_author(orcid)
        if not author:
            raise HTTPException(404, f"Aucun chercheur OpenAlex trouvé pour l'ORCID {orcid}")
        author_id = author["id"].rsplit("/", 1)[-1]
        works = fetch_author_works(author_id, limit=12)
        body.interests = generate_interests(author, works)
        orcid_nom = author.get("display_name")

    conn = db_connect()
    try:
        existing = get_profile(conn, body.username)
        if existing != (body.interests, EMBEDDING_MODEL):
            embedding = embed_texts([body.interests])[0]
            upsert_profile(conn, body.username, body.interests, embedding, EMBEDDING_MODEL)
        recos = find_top_articles(conn, body.username, 10)
        return {
            "username": body.username,
            "orcid": orcid_nom,
            "interests": body.interests,
            "recommandations": recos,
        }
    finally:
        conn.close()


@app.post("/profiles/{username}/collect")
def collect_for_profile(username: str, limit: int = 20, days: int = 365):
    """Collecte des articles correspondant aux intérêts du profil.

    La requête mélange l'intérêt déclaré et les clics récents : elle s'adapte
    à terme à la dérive du chercheur, sans jamais l'interdire.
    """
    if limit < 1 or limit > 50:
        raise HTTPException(422, "limit doit être compris entre 1 et 50")
    conn = db_connect()
    try:
        profile = get_profile(conn, username)
        if not profile:
            raise HTTPException(404, "Profil inconnu")

        clicked = get_recent_clicked(conn, username, limit=10)
        query = extract_search_terms(profile[0], clicked_titles=clicked)
        articles = search_articles(query, days=days, limit=limit)
        if not articles:
            return {"username": username, "requete": query, "ajoutes": 0}

        embeddings = embed_articles(articles)
        insert_articles(conn, articles, embeddings)
        return {
            "username": username,
            "requete": query,
            "ajoutes": len(articles),
            "articles": [{"name": a["name"], "journal": a["journal"]} for a in articles],
        }
    finally:
        conn.close()


@app.get("/profiles/{username}/recommendations")
def recommendations(username: str, limit: int = 10):
    if limit < 1 or limit > 100:
        raise HTTPException(422, "limit doit être compris entre 1 et 100")
    conn = db_connect()
    try:
        if not get_profile(conn, username):
            raise HTTPException(404, "Profil inconnu")
        return find_top_articles(conn, username, limit)
    finally:
        conn.close()


@app.post("/profiles/{username}/newsletter")
def generate_newsletter(username: str, limit: int = 10):
    """Génère la newsletter : intro + accroches rédigées par LLM, liens trackés."""
    conn = db_connect()
    try:
        profile = get_profile(conn, username)
        if not profile:
            raise HTTPException(404, "Profil inconnu")
        articles = find_top_articles(conn, username, limit)
        if not articles:
            raise HTTPException(409, "Aucun article en base : lance d'abord la collecte")

        content = generate_content(profile[0], articles)
        tracked_urls = {
            a["openalex_id"]: f"{BASE_URL}/r/{make_token(username, a['id'])}"
            for a in articles
        }
        html = build_newsletter_html(username, profile[0], articles, content, tracked_urls)
        # La génération vaut envoi : ces articles ne seront plus recommandés.
        record_recommended(conn, username, [a["id"] for a in articles])
        return {
            "username": username,
            "intro": content["intro"],
            "articles": [
                {
                    "name": a["name"],
                    "abstract": a["abstract"],
                    "accroche": content["accroches"].get(short_id(a["openalex_id"]), ""),
                    "tracked_url": tracked_urls[a["openalex_id"]],
                    "similarity": a["similarity"],
                }
                for a in articles
            ],
            "html": html,
        }
    finally:
        conn.close()


@app.get("/r/{token}")
def clicked(token: str):
    """Enregistre le clic, affine l'embedding du profil, redirige vers l'article."""
    try:
        payload = read_token(token)
    except Exception:
        raise HTTPException(400, "Lien invalide ou expiré")
    username, article_id = payload["u"], payload["a"]

    conn = db_connect()
    try:
        art = get_article(conn, article_id)
        if not art:
            raise HTTPException(404, "Article inconnu")
        log_click(conn, username, article_id)
        update_profile_embedding(conn, username, article_id, weight=EMBEDDING_WEIGHT)
    finally:
        conn.close()
    return RedirectResponse(article_url(art), status_code=302)


@app.get("/newsletter/{username}", response_class=HTMLResponse)
def newsletter_preview(username: str):
    """Version HTML directement consultable (aperçu du mail)."""
    result = generate_newsletter(username)
    return HTMLResponse(content=result["html"])
