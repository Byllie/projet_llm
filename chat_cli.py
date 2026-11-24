"""Discussion dans le terminal, en passant par l'API du chatbot."""

import os

import requests


def main():
    url = os.environ.get("CHAT_API_URL", "http://api:8000").rstrip("/")
    history, article_ids = [], []
    print("Assistant scientifique — /new : nouvelle recherche ; /quit : quitter")
    print("Les questions suivantes utilisent les mêmes articles jusqu'à /new.")
    while True:
        try:
            message = input("\nToi : ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if message == "/quit":
            return
        if message == "/new":
            history, article_ids = [], []
            print("Nouvelle recherche prête.")
            continue
        if not message:
            continue
        try:
            response = requests.post(f"{url}/chat", json={
                "message": message, "history": history[-12:], "article_ids": article_ids,
            }, timeout=(10, 210))
            data = response.json()
            if response.status_code != 200:
                print("Erreur :", data.get("detail", "L'API est indisponible."))
                continue
        except (requests.RequestException, ValueError):
            print("Impossible de joindre l'API. Démarre le service api et réessaie.")
            continue
        print("\nAssistant :", data["answer"])
        for source in data["sources"]:
            print(f"  [ID {source['id']}] {source['title']} — {source['doi'] or 'sans DOI'}")
        article_ids = data["article_ids"]
        history.extend([
            {"role": "user", "content": message},
            {"role": "assistant", "content": data["answer"][:4000]},
        ])


if __name__ == "__main__":
    main()
