import { useEffect, useRef, useState } from "react";
import Icon from "./Icon.jsx";
import { rememberUsername, request, safeUrl, savedUsername } from "./api.js";

const profilePath = (username) => `/profiles/${encodeURIComponent(username)}`;
const formatDate = (value) => {
  if (!value) return "Date non renseignée";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
};

function Busy({ children }) {
  return (
    <span className="busy">
      <span className="spinner" />
      {children}
    </span>
  );
}

function Modal({ title, subtitle, onClose, busy, children }) {
  const dialog = useRef(null);
  useEffect(() => {
    const previous = document.activeElement;
    dialog.current.showModal();
    return () => previous?.focus();
  }, []);
  return (
    <dialog
      ref={dialog}
      className="modal"
      aria-labelledby="dialog-title"
      onCancel={(event) => {
        event.preventDefault();
        if (!busy) onClose();
      }}
      onClick={(event) => {
        if (event.target === dialog.current && !busy) onClose();
      }}
    >
      <div className="modal-head">
        <div>
          <p className="eyebrow">VOTRE ESPACE PERSONNEL</p>
          <h2 id="dialog-title">{title}</h2>
        </div>
        <button
          className="icon-button"
          aria-label="Fermer"
          disabled={busy}
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      <p className="muted">{subtitle}</p>
      {children}
    </dialog>
  );
}

function ProfileForm({ initial, locked, onClose, onSave, onFind, onForget }) {
  const [mode, setMode] = useState("interests");
  const [username, setUsername] = useState(initial?.username || "");
  const [interests, setInterests] = useState(initial?.interests || "");
  const [orcid, setOrcid] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(event) {
    event.preventDefault();
    setPending(true);
    setError("");
    try {
      if (mode === "existing") await onFind(username.trim());
      else
        await onSave({
          username: username.trim(),
          ...(mode === "orcid"
            ? { orcid: orcid.trim() }
            : { interests: interests.trim() }),
        });
    } catch (err) {
      setError(err.message);
    } finally {
      setPending(false);
    }
  }
  return (
    <Modal
      title="Votre profil de recherche"
      subtitle="Des articles qui suivent vos intérêts, et leur évolution."
      busy={pending || locked}
      onClose={onClose}
    >
      <div className="segmented" aria-label="Méthode du profil">
        {[
          ["interests", "Mes intérêts"],
          ["orcid", "Mon ORCID"],
          ["existing", "Profil existant"],
        ].map(([key, label]) => (
          <button
            key={key}
            type="button"
            aria-pressed={mode === key}
            className={mode === key ? "selected" : ""}
            disabled={pending}
            onClick={() => {
              setMode(key);
              setError("");
            }}
          >
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={submit}>
        <label htmlFor="username">Nom du profil</label>
        <input
          id="username"
          required
          maxLength={64}
          value={username}
          disabled={pending}
          onChange={(event) => setUsername(event.target.value)}
          placeholder="Ex. fadwa"
          autoComplete="off"
        />
        {mode === "interests" && (
          <>
            <label htmlFor="interests">Vos sujets de recherche</label>
            <textarea
              id="interests"
              required
              maxLength={8000}
              rows={5}
              value={interests}
              disabled={pending}
              onChange={(event) => setInterests(event.target.value)}
              placeholder="Ex. Je m’intéresse aux modèles de langage et à l’apprentissage avec peu de données…"
            />
            <p className="field-hint">
              Quelques phrases suffisent. Vous pourrez les modifier ensuite.
            </p>
          </>
        )}
        {mode === "orcid" && (
          <>
            <label htmlFor="orcid">Identifiant ou lien ORCID</label>
            <input
              id="orcid"
              required
              value={orcid}
              disabled={pending}
              onChange={(event) => setOrcid(event.target.value)}
              placeholder="0000-0000-0000-0000"
            />
            <p className="field-hint">
              Vos intérêts seront proposés à partir de vos travaux trouvés dans
              OpenAlex.
            </p>
          </>
        )}
        {mode === "existing" && (
          <p className="field-hint">
            Retrouvez un profil enregistré avec son nom exact. Aucun mot de
            passe n’est nécessaire dans cette version locale.
          </p>
        )}
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button
          className="button primary full"
          disabled={
            pending ||
            !username.trim() ||
            (mode === "interests" && !interests.trim()) ||
            (mode === "orcid" && !orcid.trim())
          }
        >
          {pending ? (
            <Busy>Chargement du profil…</Busy>
          ) : mode === "existing" ? (
            "Retrouver mon profil"
          ) : (
            "Enregistrer mon profil"
          )}
        </button>
      </form>
      {initial && (
        <button
          className="text-button leave-profile"
          disabled={pending}
          onClick={onForget}
        >
          Quitter ce profil
        </button>
      )}
    </Modal>
  );
}

function CollectForm({ busy, onClose, onCollect }) {
  const [limit, setLimit] = useState(10);
  const [days, setDays] = useState(365);
  const [error, setError] = useState("");
  return (
    <Modal
      title="Élargir votre veille"
      subtitle="Recherchez de nouveaux articles adaptés à votre profil et à vos lectures."
      busy={busy}
      onClose={onClose}
    >
      <form
        onSubmit={async (event) => {
          event.preventDefault();
          setError("");
          try {
            await onCollect(limit, days);
          } catch (err) {
            setError(err.message);
          }
        }}
      >
        <label htmlFor="collect-limit">Nombre maximum d’articles</label>
        <input
          id="collect-limit"
          type="number"
          min="1"
          max="50"
          required
          disabled={busy}
          value={limit}
          onChange={(event) => setLimit(Number(event.target.value))}
        />
        <label htmlFor="collect-days">Période de publication</label>
        <select
          id="collect-days"
          disabled={busy}
          value={days}
          onChange={(event) => setDays(Number(event.target.value))}
        >
          <option value={7}>Les 7 derniers jours</option>
          <option value={30}>Les 30 derniers jours</option>
          <option value={365}>Les 12 derniers mois</option>
        </select>
        <p className="field-hint">
          La recherche et les embeddings peuvent prendre quelques instants.
        </p>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary full" disabled={busy}>
          {busy ? <Busy>Recherche dans OpenAlex…</Busy> : "Lancer la collecte"}
        </button>
      </form>
    </Modal>
  );
}

function ArticleCard({ article, onDiscuss }) {
  const [expanded, setExpanded] = useState(false);
  const url = safeUrl(article.doi || article.openalex_id);
  return (
    <article className="article-card">
      <div className="article-meta">
        <span className="tag">ARTICLE SCIENTIFIQUE</span>
        <span>{formatDate(article.publication_date)}</span>
      </div>
      <h3>{article.name}</h3>
      <p className="authors">
        {article.authors?.length
          ? article.authors.slice(0, 4).join(", ") +
            (article.authors.length > 4 ? " et al." : "")
          : "Auteurs non renseignés"}
      </p>
      {article.abstract && (
        <>
          <p className={`abstract ${expanded ? "expanded" : ""}`}>
            {article.abstract}
          </p>
          <button
            className="text-button abstract-toggle"
            onClick={() => setExpanded(!expanded)}
            aria-expanded={expanded}
          >
            {expanded ? "Réduire le résumé" : "Voir le résumé complet"}
          </button>
        </>
      )}
      <div className="article-actions">
        {url && (
          <a
            className="article-link"
            href={url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Icon name="link" size={16} />
            Lire l’article
          </a>
        )}
        <button className="text-button" onClick={() => onDiscuss(article)}>
          <Icon name="chat" size={17} />
          En discuter
        </button>
      </div>
    </article>
  );
}

function ChatPanel({ messages, busy, onSend, onClose, onReset }) {
  const [draft, setDraft] = useState("");
  const list = useRef(null);
  const input = useRef(null);
  useEffect(() => {
    list.current?.scrollTo?.({
      top: list.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages, busy]);
  useEffect(() => {
    input.current?.focus();
  }, []);
  function submit(event) {
    event.preventDefault();
    if (draft.trim() && !busy) {
      onSend(draft.trim());
      setDraft("");
    }
  }
  return (
    <aside className="chat-panel" aria-label="Assistant scientifique">
      <div className="chat-header">
        <div className="assistant-symbol">
          <Icon name="spark" />
        </div>
        <div>
          <h2>Assistant scientifique</h2>
          <span>Explorez les articles ensemble</span>
        </div>
        <button
          className="icon-button"
          aria-label="Fermer la discussion"
          onClick={onClose}
        >
          <Icon name="close" />
        </button>
      </div>
      <div className="chat-tools">
        <span>Basé sur les articles de votre bibliothèque</span>
        <button className="text-button" onClick={onReset} disabled={busy}>
          Nouvelle discussion
        </button>
      </div>
      <div
        className="chat-messages"
        ref={list}
        aria-live="polite"
        aria-relevant="additions"
      >
        {!messages.length && (
          <div className="chat-intro">
            <span className="large-symbol">
              <Icon name="chat" size={30} />
            </span>
            <h3>
              Une question fait
              <br />
              avancer la recherche.
            </h3>
            <p>
              Je peux retrouver, résumer et comparer les articles de votre
              bibliothèque.
            </p>
            <div className="suggestions">
              {[
                "Quels articles parlent du few-shot learning ?",
                "Trouve des articles sur les modèles de langage.",
              ].map((question) => (
                <button
                  key={question}
                  disabled={busy}
                  onClick={() => onSend(question)}
                >
                  {question}
                </button>
              ))}
            </div>
            <p className="field-hint">
              Mes explications reposent sur les abstracts, pas sur les textes
              intégraux.
            </p>
          </div>
        )}
        {messages.map((message, index) => (
          <div
            key={index}
            className={`message ${message.role} ${message.error ? "message-error" : ""}`}
          >
            <span className="message-label">
              {message.role === "user" ? "Vous" : "Scholar Assistant"}
            </span>
            <p>{message.content}</p>
            {message.sources?.length > 0 && (
              <div className="chat-sources">
                <span>Sources citées</span>
                {message.sources.map((source) => {
                  const url = safeUrl(source.doi);
                  return url ? (
                    <a
                      key={source.id}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      [ID {source.id}] {source.title}
                      <Icon name="link" size={14} />
                    </a>
                  ) : (
                    <span key={source.id}>
                      [ID {source.id}] {source.title}
                    </span>
                  );
                })}
              </div>
            )}
          </div>
        ))}
        {busy && (
          <div className="message assistant">
            <Busy>L’assistant consulte les articles…</Busy>
          </div>
        )}
      </div>
      <form className="chat-compose" onSubmit={submit}>
        <label className="sr-only" htmlFor="chat-message">
          Votre question
        </label>
        <textarea
          id="chat-message"
          ref={input}
          rows={2}
          maxLength={4000}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder="Posez votre question…"
          onKeyDown={(event) => {
            if (
              event.key === "Enter" &&
              !event.shiftKey &&
              !event.nativeEvent.isComposing
            ) {
              event.preventDefault();
              submit(event);
            }
          }}
        />
        <button
          className="send-button"
          aria-label="Envoyer le message"
          disabled={busy || !draft.trim()}
        >
          <Icon name="send" size={20} />
        </button>
        <p>Vérifiez les sources : les réponses peuvent contenir des erreurs.</p>
      </form>
    </aside>
  );
}

export default function App() {
  const [username, setUsername] = useState(savedUsername);
  const [profile, setProfile] = useState(null);
  const [articles, setArticles] = useState([]);
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(false);
  const [loading, setLoading] = useState(false);
  const [section, setSection] = useState("articles");
  const [modal, setModal] = useState(null);
  const [notice, setNotice] = useState(null);
  const [search, setSearch] = useState("");
  const [collecting, setCollecting] = useState(false);
  const [newsletter, setNewsletter] = useState(null);
  const [newsletterLimit, setNewsletterLimit] = useState(5);
  const [generating, setGenerating] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [messages, setMessages] = useState([]);
  const [chatIds, setChatIds] = useState([]);
  const [chatBusy, setChatBusy] = useState(false);
  const chatLock = useRef(false);
  const activeChat = useRef(null);
  const profileVersion = useRef(0);
  const locked = collecting || generating || loading || chatBusy;

  async function checkHealth(signal) {
    try {
      const data = await request("/health", { signal });
      setHealth(data);
      setHealthError(false);
    } catch (error) {
      if (!signal?.aborted) {
        setHealth(null);
        setHealthError(true);
      }
    }
  }
  useEffect(() => {
    const controller = new AbortController();
    checkHealth(controller.signal);
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (!username) return;
    const controller = new AbortController();
    setLoading(true);
    Promise.all([
      request(profilePath(username), { signal: controller.signal }),
      request(`${profilePath(username)}/recommendations?limit=10`, {
        signal: controller.signal,
      }),
    ])
      .then(([data, results]) => {
        if (!controller.signal.aborted) {
          setProfile(data);
          setArticles(results);
        }
      })
      .catch((error) => {
        if (!controller.signal.aborted)
          setNotice({ type: "error", text: error.message });
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [username]);
  useEffect(() => () => activeChat.current?.abort(), []);

  function resetChat() {
    setMessages([]);
    setChatIds([]);
  }
  function activateProfile(data, results) {
    profileVersion.current += 1;
    setProfile(data);
    setArticles(results);
    setUsername(data.username);
    rememberUsername(data.username);
    setNewsletter(null);
    setSearch("");
    resetChat();
    setModal(null);
    setNotice({
      type: "success",
      text: `Le profil « ${data.username} » est prêt. Votre veille peut commencer.`,
    });
  }
  function forgetProfile() {
    profileVersion.current += 1;
    rememberUsername("");
    setUsername("");
    setProfile(null);
    setArticles([]);
    setNewsletter(null);
    setSearch("");
    setSection("articles");
    setNotice(null);
    setModal(null);
    resetChat();
  }
  async function saveProfile(body) {
    const data = await request("/profiles", {
      method: "POST",
      body: JSON.stringify(body),
    });
    activateProfile(data, data.recommandations || []);
  }
  async function findProfile(name) {
    const [data, results] = await Promise.all([
      request(profilePath(name)),
      request(`${profilePath(name)}/recommendations?limit=10`),
    ]);
    activateProfile(data, results);
  }
  async function refreshArticles() {
    const results = await request(
      `${profilePath(username)}/recommendations?limit=10`,
    );
    setArticles(results);
  }
  async function collect(limit, days) {
    setCollecting(true);
    try {
      const data = await request(
        `${profilePath(username)}/collect?limit=${limit}&days=${days}`,
        { method: "POST" },
      );
      setModal(null);
      setNotice({
        type: "success",
        text: `${data.ajoutes} article(s) traité(s). Recherche : « ${data.requete} ».`,
      });
      try {
        await Promise.all([refreshArticles(), checkHealth()]);
      } catch (error) {
        setNotice({
          type: "error",
          text: `Collecte terminée, mais actualisation impossible : ${error.message}`,
        });
      }
    } finally {
      setCollecting(false);
    }
  }
  async function generateNewsletter() {
    if (generating) return;
    setGenerating(true);
    setNotice(null);
    try {
      const data = await request(
        `${profilePath(username)}/newsletter?limit=${newsletterLimit}`,
        { method: "POST" },
      );
      setNewsletter(data);
      try {
        await refreshArticles();
      } catch (error) {
        setNotice({
          type: "error",
          text: `Newsletter créée. Actualisation des recommandations impossible : ${error.message}`,
        });
      }
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setGenerating(false);
    }
  }
  async function sendChat(message, article = null) {
    if (chatLock.current) return;
    chatLock.current = true;
    setChatBusy(true);
    setChatOpen(true);
    const controller = new AbortController();
    activeChat.current = controller;
    const version = profileVersion.current;
    if (article) setChatIds([article.id]);
    const history = article
      ? []
      : messages
          .filter((item) => !item.error)
          .slice(-12)
          .map(({ role, content }) => ({
            role,
            content: content.slice(0, 4000),
          }));
    setMessages((previous) => [
      ...(article ? [] : previous),
      { role: "user", content: message },
    ]);
    try {
      const data = await request("/chat", {
        method: "POST",
        signal: controller.signal,
        body: JSON.stringify({
          message,
          history,
          article_ids: article ? [article.id] : chatIds,
        }),
      });
      if (version !== profileVersion.current) return;
      setChatIds(data.article_ids);
      setMessages((previous) => [
        ...previous,
        { role: "assistant", content: data.answer, sources: data.sources },
      ]);
    } catch (error) {
      if (!controller.signal.aborted && version === profileVersion.current)
        setMessages((previous) => [
          ...previous,
          { role: "assistant", content: error.message, error: true },
        ]);
    } finally {
      chatLock.current = false;
      setChatBusy(false);
    }
  }
  function discuss(article) {
    sendChat(
      `Résume l’article « ${article.name} » et explique son sujet simplement.`,
      article,
    );
  }
  const filteredArticles = articles.filter((article) =>
    `${article.name} ${article.abstract || ""} ${(article.authors || []).join(" ")}`
      .toLocaleLowerCase()
      .includes(search.toLocaleLowerCase()),
  );

  return (
    <div className={`app-shell ${chatOpen ? "with-chat" : ""}`}>
      <a className="skip-link" href="#main">
        Aller au contenu
      </a>
      <aside className="sidebar">
        <a
          className="brand"
          href="#"
          onClick={(event) => {
            event.preventDefault();
            setSection("articles");
          }}
        >
          <span className="brand-symbol">
            s<span>.</span>
          </span>
          <span>
            scholar<span className="brand-second">digest</span>
          </span>
        </a>
        <p className="nav-caption">VOTRE ESPACE</p>
        <nav aria-label="Navigation principale">
          <button
            className={section === "articles" ? "nav-item active" : "nav-item"}
            onClick={() => setSection("articles")}
          >
            <Icon name="grid" />
            Ma veille
            <span className="nav-count">{profile ? articles.length : "—"}</span>
          </button>
          <button
            className={
              section === "newsletter" ? "nav-item active" : "nav-item"
            }
            onClick={() => setSection("newsletter")}
          >
            <Icon name="mail" />
            Newsletter
          </button>
          <button
            className={chatOpen ? "nav-item active" : "nav-item"}
            onClick={() => setChatOpen(!chatOpen)}
          >
            <Icon name="chat" />
            Assistant<span className="new-badge">IA</span>
          </button>
        </nav>
        <div className="sidebar-note">
          <Icon name="book" size={22} />
          <h3>
            La recherche avance.
            <br />
            Votre veille aussi.
          </h3>
          <p>Moins de bruit, plus de découvertes utiles.</p>
        </div>
        <div className="sidebar-footer">
          <span className="avatar">
            {(profile?.username || "V").slice(0, 1).toUpperCase()}
          </span>
          <div>
            <strong>{profile?.username || "Votre profil"}</strong>
            <span>Espace de recherche local</span>
          </div>
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <span className="breadcrumb">
            Mon espace <span>/</span>{" "}
            <strong>
              {section === "articles" ? "Ma veille" : "Newsletter"}
            </strong>
          </span>
          <button
            className="profile-button"
            disabled={locked}
            onClick={() => setModal("profile")}
          >
            <Icon name="user" size={17} />
            {profile ? "Gérer mon profil" : "Configurer mon profil"}
          </button>
        </header>
        <main id="main">
          <div className="page-heading">
            <div>
              <p className="eyebrow">VOTRE VEILLE SCIENTIFIQUE</p>
              <h1>
                {section === "articles"
                  ? "Les idées qui font avancer."
                  : "Votre recherche, à la une."}
              </h1>
              <p className="lead">
                {section === "articles"
                  ? "Des articles à découvrir. De nouvelles pistes à explorer."
                  : "Une sélection commentée, réunie dans votre newsletter."}
              </p>
            </div>
            <span className="heading-mark">
              <Icon name={section === "articles" ? "book" : "mail"} size={31} />
            </span>
          </div>
          <div className="health-line">
            <span
              className={
                health ? "connection-dot" : "connection-dot disconnected"
              }
            />
            <span>
              {health
                ? `${health.articles} article${health.articles > 1 ? "s" : ""} dans la bibliothèque`
                : healthError
                  ? "Connexion à la bibliothèque indisponible"
                  : "Connexion à la bibliothèque…"}
            </span>
            {healthError && (
              <button className="text-button" onClick={() => checkHealth()}>
                Réessayer
              </button>
            )}
          </div>
          {notice && (
            <div
              className={`notice ${notice.type}`}
              role={notice.type === "error" ? "alert" : "status"}
            >
              <Icon
                name={notice.type === "error" ? "info" : "check"}
                size={19}
              />
              <span>{notice.text}</span>
              <button
                className="icon-button"
                aria-label="Masquer le message"
                onClick={() => setNotice(null)}
              >
                <Icon name="close" size={16} />
              </button>
            </div>
          )}

          {!profile && !loading && (
            <section className="welcome-card">
              <div className="welcome-copy">
                <span className="pill">
                  <Icon name="spark" size={15} />
                  Une veille à votre image
                </span>
                <h2>
                  Votre prochaine découverte
                  <br />
                  commence par vos intérêts.
                </h2>
                <p>
                  Décrivez vos sujets de recherche ou renseignez votre ORCID.
                  Retrouvez les articles qui comptent pour vous, dans un seul
                  espace.
                </p>
                <button
                  className="button primary"
                  onClick={() => setModal("profile")}
                >
                  <Icon name="plus" size={18} />
                  Créer ou retrouver mon profil
                </button>
              </div>
              <div className="research-visual" aria-hidden="true">
                <div className="orbit orbit-one" />
                <div className="orbit orbit-two" />
                <span className="orbit-core">
                  <Icon name="book" size={37} />
                </span>
                <span className="orbit-point point-one">
                  <Icon name="search" size={19} />
                </span>
                <span className="orbit-point point-two">
                  <Icon name="spark" size={20} />
                </span>
                <span className="orbit-point point-three">
                  <Icon name="mail" size={18} />
                </span>
                <span className="visual-label">Relier les idées.</span>
              </div>
            </section>
          )}

          {!profile && !loading && (
            <div className="feature-grid">
              {[
                [
                  "user",
                  "Une sélection personnelle",
                  "Vos intérêts donnent le cap à vos recommandations.",
                ],
                [
                  "search",
                  "Une bibliothèque qui s’enrichit",
                  "Collectez de nouveaux articles depuis OpenAlex.",
                ],
                [
                  "chat",
                  "Des articles à comprendre",
                  "Posez vos questions et retrouvez les sources.",
                ],
              ].map(([icon, title, text]) => (
                <section className="feature" key={title}>
                  <span>
                    <Icon name={icon} />
                  </span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </section>
              ))}
            </div>
          )}

          {loading && (
            <section className="loading-state" role="status">
              <Busy>Chargement de votre espace de recherche…</Busy>
            </section>
          )}

          {profile && !loading && (
            <div className="content-layout">
              <div className="primary-content">
                {section === "articles" ? (
                  <>
                    <div className="section-heading">
                      <div>
                        <h2>
                          À lire pour vous{" "}
                          <span className="count-badge">{articles.length}</span>
                        </h2>
                        <p>Votre sélection, selon votre profil de recherche.</p>
                      </div>
                      <button
                        className="button primary small"
                        disabled={locked}
                        onClick={() => setModal("collect")}
                      >
                        <Icon name="plus" size={17} />
                        Collecter des articles
                      </button>
                    </div>
                    <div className="search-row">
                      <label className="search-field">
                        <Icon name="search" size={19} />
                        <input
                          aria-label="Filtrer les articles affichés"
                          placeholder="Rechercher dans cette sélection…"
                          value={search}
                          onChange={(event) => setSearch(event.target.value)}
                        />
                      </label>
                      <button
                        className="icon-button outlined"
                        aria-label="Actualiser les recommandations"
                        disabled={locked}
                        onClick={async () => {
                          setLoading(true);
                          try {
                            await refreshArticles();
                          } catch (error) {
                            setNotice({ type: "error", text: error.message });
                          } finally {
                            setLoading(false);
                          }
                        }}
                      >
                        <Icon name="refresh" size={18} />
                      </button>
                    </div>
                    <div className="articles-list">
                      {filteredArticles.map((article) => (
                        <ArticleCard
                          key={article.id}
                          article={article}
                          onDiscuss={discuss}
                        />
                      ))}
                    </div>
                    {!filteredArticles.length && (
                      <div className="empty-state">
                        <Icon name="search" size={30} />
                        <h3>
                          {search
                            ? "Aucun résultat dans cette sélection"
                            : "De nouvelles lectures vous attendent"}
                        </h3>
                        <p>
                          {search
                            ? "Essayez un autre titre, auteur ou mot-clé."
                            : "Lancez une collecte pour trouver des articles. Les articles déjà proposés en newsletter sont exclus de cette liste."}
                        </p>
                        {!search && (
                          <button
                            className="button secondary"
                            disabled={locked}
                            onClick={() => setModal("collect")}
                          >
                            Rechercher des articles
                          </button>
                        )}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div className="section-heading">
                      <div>
                        <h2>Votre édition scientifique</h2>
                        <p>
                          Une introduction et les points à retenir de chaque
                          article.
                        </p>
                      </div>
                    </div>
                    <div className="newsletter-controls">
                      <div className="newsletter-icon">
                        <Icon name="mail" size={28} />
                      </div>
                      <div>
                        <h3>Préparer une nouvelle édition</h3>
                        <p>
                          La génération retire les articles sélectionnés des
                          prochaines recommandations. Aucun e-mail n’est envoyé.
                        </p>
                      </div>
                      <div className="newsletter-options">
                        <label htmlFor="newsletter-limit">
                          Articles maximum
                        </label>
                        <select
                          id="newsletter-limit"
                          value={newsletterLimit}
                          disabled={generating}
                          onChange={(event) =>
                            setNewsletterLimit(Number(event.target.value))
                          }
                        >
                          {[3, 5, 10].map((n) => (
                            <option key={n} value={n}>
                              {n} articles
                            </option>
                          ))}
                        </select>
                        <button
                          className="button primary"
                          disabled={locked || !articles.length}
                          onClick={generateNewsletter}
                        >
                          {generating ? (
                            <Busy>Rédaction en cours…</Busy>
                          ) : (
                            "Générer la newsletter"
                          )}
                        </button>
                      </div>
                    </div>
                    {newsletter ? (
                      <section
                        className="newsletter-result"
                        aria-label="Newsletter générée"
                      >
                        <div className="newsletter-masthead">
                          <span>SCHOLAR DIGEST</span>
                          <Icon name="book" size={24} />
                        </div>
                        <p className="eyebrow">
                          VOTRE ÉDITION · {profile.username}
                        </p>
                        <h2>
                          Des idées pour nourrir
                          <br />
                          votre recherche.
                        </h2>
                        <p className="newsletter-intro">{newsletter.intro}</p>
                        {newsletter.articles.map((article, index) => {
                          const url = safeUrl(article.tracked_url);
                          return (
                            <article key={index} className="newsletter-article">
                              <h3>{article.name}</h3>
                              <p>{article.accroche}</p>
                              {article.abstract && (
                                <details>
                                  <summary>Lire l’abstract</summary>
                                  <p className="abstract expanded">
                                    {article.abstract}
                                  </p>
                                </details>
                              )}
                              {url && (
                                <a
                                  href={url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="article-link"
                                >
                                  <Icon name="link" size={16} />
                                  Lire l’article
                                </a>
                              )}
                            </article>
                          );
                        })}
                        <p className="newsletter-footnote">
                          Les liens de cette édition affinent votre profil
                          lorsque vous les ouvrez.
                        </p>
                      </section>
                    ) : (
                      !generating && (
                        <div className="empty-state newsletter-empty">
                          <Icon name="mail" size={32} />
                          <h3>Votre première édition commence ici.</h3>
                          <p>
                            {articles.length
                              ? "Choisissez le nombre d’articles et laissez l’assistant préparer votre sélection commentée."
                              : "Collectez d’abord des articles dans « Ma veille » pour préparer votre newsletter."}
                          </p>
                        </div>
                      )
                    )}
                  </>
                )}
              </div>
              <aside className="context-column">
                <section className="profile-summary">
                  <div className="card-label">
                    <Icon name="user" size={17} />
                    <span>VOTRE PROFIL</span>
                  </div>
                  <h3>{profile.username}</h3>
                  <p>{profile.interests}</p>
                  <button
                    className="text-button"
                    disabled={locked}
                    onClick={() => setModal("profile")}
                  >
                    Modifier mes intérêts
                  </button>
                </section>
                <section className="assistant-card">
                  <span className="assistant-symbol">
                    <Icon name="spark" size={21} />
                  </span>
                  <h3>
                    Une lecture,
                    <br />
                    une question ?
                  </h3>
                  <p>
                    Votre assistant vous aide à comprendre les articles, sources
                    à l’appui.
                  </p>
                  <button
                    className="button secondary full"
                    onClick={() => setChatOpen(true)}
                  >
                    Ouvrir l’assistant
                  </button>
                </section>
              </aside>
            </div>
          )}
          <footer className="page-footer">
            <span>Scholar Digest</span>
            <p>Votre curiosité. De nouvelles perspectives.</p>
            <span>Sources : OpenAlex</span>
          </footer>
        </main>
      </div>
      {!chatOpen && (
        <button className="chat-fab" onClick={() => setChatOpen(true)}>
          <Icon name="chat" size={21} />
          <span>Une question ?</span>
        </button>
      )}
      {chatOpen && (
        <ChatPanel
          messages={messages}
          busy={chatBusy}
          onSend={sendChat}
          onClose={() => setChatOpen(false)}
          onReset={resetChat}
        />
      )}
      {modal === "profile" && (
        <ProfileForm
          initial={profile}
          locked={false}
          onClose={() => setModal(null)}
          onSave={saveProfile}
          onFind={findProfile}
          onForget={forgetProfile}
        />
      )}
      {modal === "collect" && (
        <CollectForm
          busy={collecting}
          onClose={() => setModal(null)}
          onCollect={collect}
        />
      )}
    </div>
  );
}
