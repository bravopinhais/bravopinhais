/**
 * Bootstrap opt-in da autenticação do Bravo Shadow.
 *
 * Permanece fechado sem configuração explícita. Não descobre APIs,
 * não usa endpoints de produção e não inicia rede quando desabilitado.
 */
import { initializeGoogleSession } from "./google-auth.js";
import { createBravoApiClient } from "./bravo-api.js";

const root = document.getElementById("bravo-auth-root");
if (root) {
  const status = document.createElement("span");
  status.className = "api-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  root.replaceChildren(status);

  const config = window.BRAVO_SHADOW_CONFIG;
  const disabledMessage = "Login Google bloqueado: API HTTPS e configuração Shadow ainda não confirmadas.";

  function showStatus(message, state = "") {
    status.textContent = message;
    status.className = state ? `api-status ${state}` : "api-status";
  }

  function validateConfig(value) {
    if (!value || value.enabled !== true) {
      throw new Error(disabledMessage);
    }
    if (typeof value.clientId !== "string" || !value.clientId.trim()) {
      throw new Error("Client ID Google ausente.");
    }
    if (typeof value.apiBase !== "string" || !value.apiBase.trim()) {
      throw new Error("URL HTTPS da API Shadow ausente.");
    }

    const api = new URL(value.apiBase);
    const local = ["localhost", "127.0.0.1"].includes(api.hostname);
    if (api.protocol !== "https:" && !(local && api.protocol === "http:")) {
      throw new Error("A API Shadow precisa usar HTTPS.");
    }
    if (api.origin !== window.location.origin || api.pathname !== "/" ||
        api.search || api.hash || api.username || api.password) {
      throw new Error("A API deve usar a mesma origem HTTPS desta homologação.");
    }
    return { clientId: value.clientId.trim(), apiBase: api.origin };
  }

  let sessionController = null;
  let apiClient = null;
  let disposed = false;

  function renderSignedOut(message = "Aguardando autenticação Google.") {
    root.replaceChildren(status);
    showStatus(message);
    const buttonHost = document.createElement("div");
    buttonHost.id = "bravo-google-button";
    buttonHost.setAttribute("aria-label", "Entrar com Google");
    root.append(buttonHost);
    return buttonHost;
  }

  async function start() {
    let settings;
    try {
      settings = validateConfig(config);
    } catch (error) {
      showStatus(error.message || disabledMessage);
      return;
    }

    const buttonHost = renderSignedOut("Carregando autenticação Google…");
    try {
      sessionController = await initializeGoogleSession({
        ...settings,
        buttonElement: buttonHost,
        onAuthenticated(session) {
          if (disposed) return;
          apiClient = createBravoApiClient({
            apiBase: settings.apiBase,
            getAuthorizationHeader: session.getAuthorizationHeader,
          });
          window.dispatchEvent(new CustomEvent("bravo:session-ready", {
            detail: { api: apiClient, user: session.user },
          }));
          root.replaceChildren();
          const identity = document.createElement("span");
          identity.className = "api-status ok";
          identity.textContent = `${session.user.email} · ${session.user.profile}`;
          const signOut = document.createElement("button");
          signOut.type = "button";
          signOut.className = "action-btn";
          signOut.textContent = "Sair";
          signOut.addEventListener("click", () => {
            apiClient = null;
            session.signOut();
            window.dispatchEvent(new CustomEvent("bravo:session-ended"));
            renderSignedOut("Sessão encerrada.");
          });
          root.append(identity, signOut);
        },
        onError(error) {
          apiClient = null;
          window.dispatchEvent(new CustomEvent("bravo:session-ended"));
          showStatus(error.message || "Não foi possível autenticar.", "err");
        },
      });
      if (!disposed && !sessionController.user) {
        showStatus("Entre com uma conta Google cadastrada e ativa no Bravo.");
      }
    } catch (error) {
      showStatus(error.message || "Não foi possível inicializar o Google.", "err");
    }
  }

  // Mantém o cliente encapsulado neste módulo; os módulos de negócio serão
  // conectados por etapas após homologação do endpoint e das permissões.
  void apiClient;
  void start();

  window.addEventListener("pagehide", () => {
    disposed = true;
    apiClient = null;
    window.dispatchEvent(new CustomEvent("bravo:session-ended"));
    sessionController?.dispose();
  }, { once: true });
}
