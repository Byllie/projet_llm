export async function request(path, { signal, ...options } = {}) {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timer = setTimeout(abort, 300000);
  try {
    const response = await fetch(`/api${path}`, {
      ...options,
      headers: { "Content-Type": "application/json", ...options.headers },
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = data?.detail;
      const message =
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail.map((item) => item.msg).join(" · ")
            : "L’API ne répond pas correctement. Vérifie que le service api est démarré.";
      const error = new Error(message);
      error.status = response.status;
      throw error;
    }
    if (data === null) throw new Error("La réponse du serveur est illisible.");
    return data;
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error.name === "AbortError")
      throw new Error(
        "Le délai est dépassé. Vérifie le résultat avant de relancer cette action.",
      );
    if (error instanceof TypeError)
      throw new Error("Connexion impossible. Vérifie que l’API est démarrée.");
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}

export function safeUrl(value) {
  if (!value) return null;
  try {
    const url = new URL(value);
    return ["http:", "https:"].includes(url.protocol) ? url.href : null;
  } catch {
    return null;
  }
}

export function savedUsername() {
  try {
    return localStorage.getItem("scholar.username") || "";
  } catch {
    return "";
  }
}

export function rememberUsername(value) {
  try {
    localStorage.setItem("scholar.username", value);
  } catch {
    /* L'application reste utilisable sans stockage local. */
  }
}
