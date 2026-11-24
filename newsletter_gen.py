"""Génération du contenu de la newsletter : intro et accroches via OpenAI."""

import json
import os

import requests

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_CHAT_URL = "https://api.openai.com/v1/chat/completions"
CHAT_MODEL = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o-mini")

PROMPT = """Tu rédiges une newsletter scientifique hebdomadaire pour une chercheuse ou un chercheur.

Ses intérêts : {interests}

Voici les articles sélectionnés cette semaine :
{liste}

Rédige en français :
- une introduction de 2-3 phrases qui relie les articles aux intérêts du chercheur ;
- pour chaque article, une accroche de 2-3 phrases expliquant pourquoi il peut l'intéresser (concret, sans superlatifs marketing).

Réponds uniquement en JSON : {{"intro": "...", "accroches": [{{"openalex_id": "...", "texte": "..."}}]}}"""


def build_prompt(interests, articles):
    liste = "\n".join(
        f"- id: {a['openalex_id']}\n  titre: {a['name']}\n  abstract: {(a.get('abstract') or '')[:600]}"
        for a in articles
    )
    return PROMPT.format(interests=interests, liste=liste)


def short_id(openalex_id):
    """Forme courte d'un id OpenAlex (W4403884017), quel que soit le format fourni."""
    return openalex_id.rsplit("/", 1)[-1]


def generate_content(interests, articles):
    """Appelle OpenAI et retourne {"intro": str, "accroches": {id_court: texte}}."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY manquante.")
    resp = requests.post(
        OPENAI_CHAT_URL,
        headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
        json={
            "model": CHAT_MODEL,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": "Tu es un assistant de veille scientifique."},
                {"role": "user", "content": build_prompt(interests, articles)},
            ],
        },
        timeout=90,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Erreur OpenAI {resp.status_code} : {resp.text[:200]}")
    content = json.loads(resp.json()["choices"][0]["message"]["content"])
    accroches = {
        short_id(a["openalex_id"]): a["texte"]
        for a in content.get("accroches", [])
        if "openalex_id" in a and "texte" in a
    }
    return {"intro": content.get("intro", ""), "accroches": accroches}


def build_newsletter_html(username, interests, articles, content, tracked_urls):
    """Assemble le HTML de l'email avec les liens trackés.

    articles : liste ordonnée ; tracked_urls : {openalex_id: url trackée}
    """
    parts = [
        "<html><body>",
        f"<p>Bonjour {username},</p>",
        f"<p>{content['intro']}</p>",
        "<hr>",
    ]
    for art in articles:
        url = tracked_urls.get(art["openalex_id"], "#")
        accroche = content["accroches"].get(short_id(art["openalex_id"]), "")
        auteurs = ", ".join(art.get("authors") or [])
        parts.append(f"<h3>{art['name']}</h3>")
        parts.append(f"<p><em>{auteurs}</em></p>")
        parts.append(f"<p>{accroche}</p>")
        if art.get("abstract"):
            parts.append(f"<p><strong>Résumé :</strong> {art['abstract']}</p>")
        parts.append(f'<p><a href="{url}">Lire l\'article</a></p>')
        parts.append("<hr>")
    parts.append(
        "<p>Les liens ci-dessus sont trackés : ton clic affine tes recommandations "
        "de la semaine prochaine.<br>Vos préférences : " + interests + "</p>"
    )
    parts.append("</body></html>")
    return "\n".join(parts)
