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

## Interface React

Démarrer l'interface et l'API (la base existante est conservée) :

```bash
sudo env -u OPENAI_API_KEY docker compose --env-file .env up -d --build api frontend
```

Ouvrir [http://localhost:5173](http://localhost:5173).
Aucune installation de Node.js n'est nécessaire avec Docker.

- Créer un profil avec ses intérêts ou un ORCID, ou retrouver un profil existant.
- Collecter des articles, consulter les recommandations et leurs abstracts.
- Cliquer sur « En discuter » pour interroger le chatbot sur un article précis.
- Dans « Newsletter », générer une édition avec les liens trackés.

Le nom du dernier profil est mémorisé dans le navigateur. Le profil est chargé
depuis la base sans recalcul de son embedding. Cette version locale n'a pas
d'authentification : le nom du profil n'est pas un mot de passe.
« Quitter ce profil » revient à l'accueil sans supprimer les données en base.
Les conversations et la dernière newsletter affichée restent en mémoire pendant
la session. « Nouvelle discussion » permet de changer de sujet.

La génération d'une newsletter marque ses articles comme déjà proposés et les
retire des recommandations. Elle n'envoie pas d'e-mail. Les liens trackés restent
ceux de l'API (`APP_BASE_URL`, par défaut `http://localhost:8000`).

Les clés API restent dans le backend. Le frontend utilise le proxy `/api` ;
aucune clé ne doit être ajoutée dans un fichier `VITE_*`.

Pour développer sans reconstruire l'image (Node.js 20.19+ ou 22+) :

```bash
cd frontend
npm ci
npm run dev
```

L'API doit tourner sur le port 8000. `API_PROXY_TARGET` permet de changer cette
adresse pour le serveur de développement. Pour vérifier l'interface :

```bash
npm test
npm run build
```

Les tests de l'interface simulent l'API et ne font aucun appel OpenAI.

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

Les origines locales sur les ports 5173 et 3000 sont autorisées.
`FRONTEND_ORIGINS` permet de changer cette liste pour un client direct.
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
