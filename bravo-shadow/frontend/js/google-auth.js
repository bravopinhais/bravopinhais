/**
 * Sessão Google do Bravo Shadow.
 *
 * O ID token é mantido somente em memória e validado pela API do Bravo.
 * Este módulo não grava credenciais em localStorage, sessionStorage ou cookies.
 */

let googleSdkPromise;

function loadGoogleIdentityServices() {
  if (window.google?.accounts?.id) return Promise.resolve(window.google.accounts.id);
  if (googleSdkPromise) return googleSdkPromise;

  googleSdkPromise = new Promise((resolve, reject) => {
    const existing = document.querySelector('script[data-bravo-google-identity]');
    const script = existing || document.createElement("script");

    const fail = () => {
      googleSdkPromise = undefined;
      reject(new Error("Não foi possível carregar a autenticação Google."));
    };

    script.addEventListener("load", () => {
      if (window.google?.accounts?.id) resolve(window.google.accounts.id);
      else fail();
    }, { once: true });
    script.addEventListener("error", fail, { once: true });

    if (!existing) {
      script.src = "https://accounts.google.com/gsi/client";
      script.async = true;
      script.defer = true;
      script.dataset.bravoGoogleIdentity = "true";
      document.head.appendChild(script);
    }
  });

  return googleSdkPromise;
}

function validateApiBase(apiBase) {
  if (typeof apiBase !== "string" || !apiBase.trim()) {
    throw new Error("A URL da API do Bravo ainda não foi configurada.");
  }

  const url = new URL(apiBase.trim(), window.location.origin);
  const localHost = ["localhost", "127.0.0.1"].includes(url.hostname);
  if (url.protocol !== "https:" && !(url.protocol === "http:" && localHost)) {
    throw new Error("A API de autenticação precisa usar HTTPS.");
  }
  return url.href.replace(/\/+$/, "");
}

/**
 * Inicializa o botão Google e confirma o cadastro/estado do usuário na API.
 * @param {{clientId:string, apiBase:string, buttonElement:HTMLElement,
 * onAuthenticated:(session:object)=>void, onError:(error:Error)=>void}} options
 */
export async function initializeGoogleSession({
  clientId,
  apiBase,
  buttonElement,
  onAuthenticated,
  onError = () => {},
}) {
  if (!clientId || typeof clientId !== "string") {
    throw new Error("O Client ID público do Google não foi configurado.");
  }
  if (!(buttonElement instanceof HTMLElement)) {
    throw new Error("O espaço do botão Google não foi encontrado.");
  }

  const apiRoot = validateApiBase(apiBase);
  const googleId = await loadGoogleIdentityServices();
  let idToken = null;
  let currentUser = null;
  let disposed = false;

  const clearSession = () => {
    idToken = null;
    currentUser = null;
    googleId.disableAutoSelect();
  };

  const handleCredential = async ({ credential } = {}) => {
    if (disposed) return;
    if (typeof credential !== "string" || !credential) {
      clearSession();
      onError(new Error("O Google não retornou uma credencial válida."));
      return;
    }

    try {
      const response = await fetch(apiRoot + "/api/v1/auth/me", {
        method: "GET",
        headers: { Authorization: "Bearer " + credential },
        cache: "no-store",
        credentials: "omit",
        referrerPolicy: "no-referrer",
      });

      if (!response.ok) {
        let message = "Acesso não autorizado pelo Bravo.";
        try {
          const body = await response.json();
          if (typeof body.detail === "string") message = body.detail;
        } catch {}
        throw new Error(message);
      }

      const user = await response.json();
      if (
        !user ||
        typeof user.email !== "string" ||
        user.status !== "Ativo" ||
        typeof user.profile !== "string"
      ) {
        throw new Error("A API não confirmou um usuário ativo cadastrado no Bravo.");
      }

      if (disposed) return;
      idToken = credential;
      currentUser = Object.freeze({
        email: user.email,
        profile: user.profile,
        status: user.status,
      });

      onAuthenticated({
        user: currentUser,
        getAuthorizationHeader: () =>
          idToken ? { Authorization: "Bearer " + idToken } : {},
        signOut: clearSession,
      });
    } catch (error) {
      clearSession();
      onError(error instanceof Error ? error : new Error("Falha na autenticação."));
    }
  };

  googleId.initialize({
    client_id: clientId,
    callback: handleCredential,
    auto_select: false,
    cancel_on_tap_outside: true,
    context: "signin",
  });

  googleId.renderButton(buttonElement, {
    type: "standard",
    theme: "outline",
    size: "large",
    text: "signin_with",
    shape: "rectangular",
    logo_alignment: "left",
    width: Math.max(220, Math.min(320, buttonElement.clientWidth || 320)),
  });

  return {
    get user() {
      return currentUser;
    },
    getAuthorizationHeader: () =>
      idToken ? { Authorization: "Bearer " + idToken } : {},
    signOut: clearSession,
    dispose() {
      disposed = true;
      clearSession();
      buttonElement.replaceChildren();
    },
  };
}
