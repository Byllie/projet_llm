import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App.jsx";
import { safeUrl } from "./api.js";

const article = {
  id: 8,
  name: "Few-shot learning for language models",
  authors: ["Alice Example"],
  abstract: "This study examines data-efficient language models.",
  publication_date: "2026-10-19",
  doi: "https://doi.org/10.1234/test",
  openalex_id: "https://openalex.org/W8",
  similarity: 0.409,
};
let fetchMock;

beforeEach(() => {
  let articles = [article];
  fetchMock = vi.fn(async (path, options = {}) => {
    const url = new URL(path, "http://localhost");
    const body = options.body ? JSON.parse(options.body) : {};
    let data;
    if (url.pathname === "/api/health") data = { status: "ok", articles: 19 };
    else if (url.pathname === "/api/profiles" && options.method === "POST")
      data = {
        username: body.username,
        interests: body.interests || "Generated interests from ORCID",
        recommandations: articles,
      };
    else if (url.pathname === "/api/profiles/alice")
      data = {
        username: "alice",
        interests: "Language models",
        embedding_model: "text-embedding-3-small",
      };
    else if (url.pathname.endsWith("/recommendations")) data = articles;
    else if (url.pathname.endsWith("/collect")) {
      articles = [
        ...articles,
        { ...article, id: 9, name: "Newly collected research" },
      ];
      data = { ajoutes: 1, requete: "language models" };
    } else if (url.pathname.endsWith("/newsletter")) {
      articles = [];
      data = {
        intro: "Your research digest.",
        articles: [
          {
            ...article,
            accroche: "Why this study matters.",
            tracked_url: "http://localhost:8000/r/signed-token",
          },
        ],
        html: "<script>unsafe()</script>",
      };
    } else if (url.pathname === "/api/chat")
      data = {
        answer: "Résumé de l’article [ID 8].",
        sources: [
          {
            id: 8,
            title: article.name,
            doi: article.doi,
            authors: article.authors,
          },
        ],
        article_ids: [8],
      };
    else
      return {
        ok: false,
        status: 404,
        json: async () => ({ detail: "Profil inconnu" }),
      };
    return { ok: true, status: 200, json: async () => data };
  });
  vi.stubGlobal("fetch", fetchMock);
});

async function existingProfile() {
  localStorage.setItem("scholar.username", "alice");
  render(<App />);
  await screen.findByRole("heading", { name: article.name });
}

function callsTo(path) {
  return fetchMock.mock.calls.filter(([url]) => url === `/api${path}`);
}

describe("research workspace", () => {
  it("creates a profile from interests and displays real returned articles", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      screen.getByRole("button", { name: "Créer ou retrouver mon profil" }),
    );
    await user.type(screen.getByLabelText("Nom du profil"), "alice");
    await user.type(
      screen.getByLabelText("Vos sujets de recherche"),
      "Language models",
    );
    await user.click(
      screen.getByRole("button", { name: "Enregistrer mon profil" }),
    );
    await screen.findByRole("heading", { name: article.name });
    expect(JSON.parse(callsTo("/profiles")[0][1].body)).toEqual({
      username: "alice",
      interests: "Language models",
    });
    expect(localStorage.getItem("scholar.username")).toBe("alice");
  });

  it("sends an ORCID without an empty interests field", async () => {
    const user = userEvent.setup();
    render(<App />);
    await user.click(
      screen.getByRole("button", { name: "Configurer mon profil" }),
    );
    await user.click(screen.getByRole("button", { name: "Mon ORCID" }));
    await user.type(screen.getByLabelText("Nom du profil"), "alice");
    await user.type(
      screen.getByLabelText("Identifiant ou lien ORCID"),
      "0000-0001-2345-6789",
    );
    await user.click(
      screen.getByRole("button", { name: "Enregistrer mon profil" }),
    );
    await screen.findByRole("heading", { name: article.name });
    expect(JSON.parse(callsTo("/profiles")[0][1].body)).toEqual({
      username: "alice",
      orcid: "0000-0001-2345-6789",
    });
  });

  it("restores an existing profile without rewriting its embedding", async () => {
    await existingProfile();
    expect(callsTo("/profiles")).toHaveLength(0);
    expect(callsTo("/profiles/alice")).toHaveLength(1);
  });

  it("leaves the local profile without deleting it from the database", async () => {
    const user = userEvent.setup();
    await existingProfile();
    await user.click(screen.getByRole("button", { name: "Gérer mon profil" }));
    await user.click(screen.getByRole("button", { name: "Quitter ce profil" }));
    await screen.findByRole("button", {
      name: "Créer ou retrouver mon profil",
    });
    expect(localStorage.getItem("scholar.username")).toBe("");
    expect(
      fetchMock.mock.calls.some(([, options]) => options?.method === "DELETE"),
    ).toBe(false);
  });

  it("collects using the selected period and refreshes recommendations", async () => {
    const user = userEvent.setup();
    await existingProfile();
    await user.click(
      screen.getByRole("button", { name: "Collecter des articles" }),
    );
    await user.clear(screen.getByLabelText("Nombre maximum d’articles"));
    await user.type(screen.getByLabelText("Nombre maximum d’articles"), "5");
    await user.selectOptions(
      screen.getByLabelText("Période de publication"),
      "30",
    );
    await user.click(
      screen.getByRole("button", { name: "Lancer la collecte" }),
    );
    await screen.findByRole("heading", { name: "Newly collected research" });
    expect(
      callsTo("/profiles/alice/collect?limit=5&days=30")[0][1].method,
    ).toBe("POST");
  });

  it("generates once, displays tracked links, and does not render server HTML", async () => {
    const user = userEvent.setup();
    await existingProfile();
    await user.click(
      screen.getByRole("button", { name: "Newsletter", exact: true }),
    );
    await user.click(
      screen.getByRole("button", { name: "Générer la newsletter" }),
    );
    await screen.findByText("Your research digest.");
    expect(
      screen.getByRole("link", { name: "Lire l’article" }),
    ).toHaveAttribute("href", "http://localhost:8000/r/signed-token");
    expect(callsTo("/profiles/alice/newsletter?limit=5")).toHaveLength(1);
    expect(document.querySelector("script")).toBeNull();
    expect(
      fetchMock.mock.calls.some(([url]) => url === "/api/newsletter/alice"),
    ).toBe(false);
    await user.click(screen.getByRole("button", { name: /Ma veille/ }));
    await screen.findByText("De nouvelles lectures vous attendent");
  });

  it("discusses an article, keeps context, and resets it for a new topic", async () => {
    const user = userEvent.setup();
    await existingProfile();
    await user.click(screen.getByRole("button", { name: "En discuter" }));
    await screen.findByText("Résumé de l’article [ID 8].");
    expect(JSON.parse(callsTo("/chat")[0][1].body).article_ids).toEqual([8]);
    await user.type(
      screen.getByLabelText("Votre question"),
      "Explique plus simplement",
    );
    await user.click(
      screen.getByRole("button", { name: "Envoyer le message" }),
    );
    await waitFor(() => expect(callsTo("/chat")).toHaveLength(2));
    expect(JSON.parse(callsTo("/chat")[1][1].body).history).toHaveLength(2);
    expect(JSON.parse(callsTo("/chat")[1][1].body).article_ids).toEqual([8]);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Nouvelle discussion" }),
      ).toBeEnabled(),
    );
    await user.click(
      screen.getByRole("button", { name: "Nouvelle discussion" }),
    );
    await user.type(screen.getByLabelText("Votre question"), "Un autre sujet");
    await user.click(
      screen.getByRole("button", { name: "Envoyer le message" }),
    );
    await waitFor(() => expect(callsTo("/chat")).toHaveLength(3));
    expect(JSON.parse(callsTo("/chat")[2][1].body)).toMatchObject({
      history: [],
      article_ids: [],
    });
  });

  it("shows a failed profile request without pretending it succeeded", async () => {
    const user = userEvent.setup();
    fetchMock.mockImplementation(async () => ({
      ok: false,
      status: 503,
      json: async () => ({ detail: "Service indisponible" }),
    }));
    render(<App />);
    await user.click(
      screen.getByRole("button", { name: "Configurer mon profil" }),
    );
    await user.type(screen.getByLabelText("Nom du profil"), "alice");
    await user.type(screen.getByLabelText("Vos sujets de recherche"), "NLP");
    await user.click(
      screen.getByRole("button", { name: "Enregistrer mon profil" }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Service indisponible",
    );
    expect(localStorage.getItem("scholar.username")).toBeNull();
  });

  it("blocks unsafe links supplied by external metadata", () => {
    expect(safeUrl("javascript:alert(1)")).toBeNull();
    expect(safeUrl("data:text/html,hello")).toBeNull();
    expect(safeUrl("https://doi.org/10.1234/test")).toBe(
      "https://doi.org/10.1234/test",
    );
  });
});
