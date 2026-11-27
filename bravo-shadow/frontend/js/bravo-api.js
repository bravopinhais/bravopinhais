/**
 * Cliente HTTP comum do Bravo Shadow.
 *
 * Não persiste tokens. Recebe o cabeçalho Bearer da sessão Google em memória
 * e envia somente para a origem HTTPS configurada da API Shadow.
 */

export class BravoApiError extends Error {
  constructor(message, { status = 0, requestId = null } = {}) {
    super(message);
    this.name = "BravoApiError";
    this.status = status;
    this.requestId = requestId;
  }
}

function normalizeApiBase(apiBase) {
  if (typeof apiBase !== "string" || !apiBase.trim()) {
    throw new BravoApiError("A API Shadow não está configurada.");
  }
  let url;
  try {
    url = new URL(apiBase.trim());
  } catch {
    throw new BravoApiError("A URL da API Shadow é inválida.");
  }
  const local = ["localhost", "127.0.0.1"].includes(url.hostname);
  if (url.protocol !== "https:" && !(local && url.protocol === "http:")) {
    throw new BravoApiError("A API Shadow deve usar HTTPS.");
  }
  if (url.username || url.password || url.search || url.hash) {
    throw new BravoApiError("A URL base da API contém componentes não permitidos.");
  }
  return url.href.replace(/\/+$/, "");
}

function normalizePath(path, base) {
  if (typeof path !== "string" || !path.startsWith("/api/v1/") || path.startsWith("//")) {
    throw new BravoApiError("Caminho de API inválido.");
  }
  const url = new URL(path, base + "/");
  if (url.origin !== new URL(base).origin || !url.pathname.startsWith("/api/v1/")) {
    throw new BravoApiError("O caminho não pertence à API Shadow configurada.");
  }
  return url.href;
}

export function createBravoApiClient({ apiBase, getAuthorizationHeader } = {}) {
  const base = normalizeApiBase(apiBase);
  if (typeof getAuthorizationHeader !== "function") {
    throw new BravoApiError("A sessão Google não forneceu o provedor de autorização.");
  }

  async function request(method, path, body, options = {}) {
    const authorization = getAuthorizationHeader();
    if (
      !authorization ||
      typeof authorization.Authorization !== "string" ||
      !/^Bearer\s+\S+$/i.test(authorization.Authorization)
    ) {
      throw new BravoApiError("Sessão Google ausente ou expirada. Entre novamente.");
    }

    const headers = new Headers(options.headers || {});
    headers.set("Authorization", authorization.Authorization);
    headers.set("Accept", "application/json");

    let payload;
    if (body !== undefined && body !== null) {
      if (body instanceof FormData || body instanceof Blob) {
        payload = body;
      } else {
        headers.set("Content-Type", "application/json");
        payload = JSON.stringify(body);
      }
    }

    let response;
    try {
      response = await fetch(normalizePath(path, base), {
        method,
        headers,
        body: payload,
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
        signal: options.signal,
        redirect: "error",
      });
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      throw new BravoApiError("Não foi possível comunicar com a API Shadow.");
    }

    const requestId = response.headers.get("X-Request-ID");
    if (response.status === 204) {
      if (!response.ok) throw new BravoApiError("A API recusou a operação.", { status: response.status, requestId });
      return null;
    }

    const contentType = response.headers.get("content-type") || "";
    let result = null;
    if (contentType.includes("application/json")) {
      try { result = await response.json(); } catch {
        throw new BravoApiError("A API retornou uma resposta inválida.", { status: response.status, requestId });
      }
    }

    if (!response.ok) {
      const detail = typeof result?.detail === "string" ? result.detail : "A API recusou a operação.";
      throw new BravoApiError(detail, { status: response.status, requestId });
    }
    return result;
  }

  return Object.freeze({
    get: (path, options) => request("GET", path, undefined, options),
    post: (path, body, options) => request("POST", path, body, options),
    put: (path, body, options) => request("PUT", path, body, options),
    patch: (path, body, options) => request("PATCH", path, body, options),
    delete: (path, options) => request("DELETE", path, undefined, options),
  });
}
