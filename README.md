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

`sudo docker compose down` arrête les services en conservant les données.
Ne pas ajouter `-v` si l'on veut conserver la base.
