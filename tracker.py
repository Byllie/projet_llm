"""Liens de tracking signés : un token contient l'utilisateur et l'article."""

import os

from itsdangerous import URLSafeSerializer


def get_serializer():
    return URLSafeSerializer(os.environ.get("API_SECRET_KEY", "dev-secret"), salt="link")


def make_token(username, article_id):
    return get_serializer().dumps({"u": username, "a": article_id})


def read_token(token):
    """Retourne {"u": username, "a": article_id} ou lève BadSignature."""
    return get_serializer().loads(token)
