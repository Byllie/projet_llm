# Recommandation d'articles

Le fichier `.env` doit contenir `OPENAI_API_KEY` et `OPENALEX_API_KEY`.
Ne pas partager ou versionner les clés.

## Collecte existante

```bash
sudo docker compose up --build
```

## Profil et top 10

Créer un profil et afficher les 10 articles les plus proches de ses intérêts :

```bash
sudo docker compose build app
sudo env -u OPENAI_API_KEY docker compose --env-file .env run --rm app python3 recommend.py --user alice --interests "Je m'intéresse au deep learning et au traitement automatique du langage."
```

Le profil est enregistré en base. Pour retrouver ses recommandations :

```bash
sudo docker compose run --rm app python3 recommend.py --user alice
```

Pour modifier les intérêts, relancer la première commande avec un nouveau texte.
Ajouter `--limit 5` pour obtenir cinq résultats. Seuls les articles en base sont utilisés.

## Chatbot scientifique

Le chatbot cherche jusqu'à cinq articles dans la base, puis utilise leurs titres
et abstracts pour répondre avec des sources. Il n'a pas accès au texte intégral.
Il peut résumer, expliquer et comparer les articles trouvés.

La clé `OPENAI_API_KEY` reste côté Python. Le modèle de discussion est
`gpt-4.1-mini` par défaut ; pour le changer, définir `OPENAI_CHAT_MODEL` dans `.env`.
La clé doit autoriser ce modèle et les embeddings. Les appels consomment du crédit API.

Démarrer l'API sans relancer la collecte :

```bash
sudo env -u OPENAI_API_KEY docker compose --env-file .env build app api
sudo env -u OPENAI_API_KEY docker compose --env-file .env up -d api
```

Vérifier le démarrage :

```bash
curl http://localhost:8000/health
```

Tester une question :

```bash
curl http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"message": "Quels articles parlent du few-shot learning ?"}'
```

Ou discuter dans le terminal :

```bash
sudo docker compose run --rm app python3 chat_cli.py
```

Exemples : « Quels articles parlent du few-shot learning ? », puis « Résume le
premier plus simplement ». Les questions de suivi utilisent les mêmes sources.
Taper `/new` pour chercher sur un autre sujet et `/quit` pour quitter.

Documentation interactive : [http://localhost:8000/docs](http://localhost:8000/docs).
`POST /chat` accepte `message`, `history` (12 messages maximum, rôles `user` et
`assistant`) et `article_ids` (IDs des sources de la réponse précédente).
Il renvoie `answer`, `sources` (titres, auteurs, DOI de la base) et `article_ids`.
Pour une nouvelle recherche, envoyer un historique et des IDs vides.

L'API est prête pour une future interface React : les origines locales sur les
ports 5173 et 3000 sont autorisées. `FRONTEND_ORIGINS` permet de changer cette liste.
Cette première version locale n'ajoute ni interface React ni authentification.
L'historique reste dans le client pendant la discussion, sans table de conversations.
La pertinence des réponses dépend des articles disponibles ; le modèle est instruit
de signaler quand les abstracts ne suffisent pas, ce qui reste à vérifier à l'usage.

Voir les erreurs de démarrage :

```bash
sudo docker compose logs --tail=50 api
```

Tests automatiques sans appel OpenAI ni base réelle :

```bash
sudo docker compose run --rm --no-deps api sh -c 'pip install -r requirements-dev.txt && python3 -m unittest -v test_chatbot'
```

`sudo docker compose down` arrête les services en conservant les données.
Ne pas ajouter `-v` si l'on veut conserver la base.
