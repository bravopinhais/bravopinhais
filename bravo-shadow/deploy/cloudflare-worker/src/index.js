const GOOGLE_CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs";
const GOOGLE_ISSUERS = new Set(["accounts.google.com", "https://accounts.google.com"]);

let cachedKeys = null;
let cachedKeysUntil = 0;

function json(body, status = 200, headers = {}) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json; charset=utf-8", ...headers },
  });
}

function corsHeaders(request, env) {
  const origin = request.headers.get("Origin");
  const allowed = typeof env.BRAVO_ALLOWED_ORIGIN === "string"
    && origin === env.BRAVO_ALLOWED_ORIGIN;
  return allowed ? {
    "access-control-allow-origin": origin,
    "access-control-allow-methods": "GET, OPTIONS",
    "access-control-allow-headers": "Authorization, Content-Type",
    "access-control-max-age": "600",
    "vary": "Origin",
  } : {};
}

function decodeBase64Url(value) {
  const normalized = value.replace(/-/g, "+").replace(/_/g, "/");
  const padded = normalized + "=".repeat((4 - normalized.length % 4) % 4);
  const binary = atob(padded);
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}

function decodeJsonPart(value) {
  return JSON.parse(new TextDecoder().decode(decodeBase64Url(value)));
}

async function getGoogleKey(kid) {
  const now = Date.now();
  if (!cachedKeys || now >= cachedKeysUntil) {
    const response = await fetch(GOOGLE_CERTS_URL, {
      headers: { accept: "application/json" },
    });
    if (!response.ok) throw new Error("Não foi possível consultar as chaves públicas Google.");
    const body = await response.json();
    cachedKeys = Array.isArray(body.keys) ? body.keys : [];
    const maxAge = Number(response.headers.get("cache-control")?.match(/max-age=(\d+)/i)?.[1] || 300);
    cachedKeysUntil = now + Math.max(60, Math.min(maxAge, 3600)) * 1000;
  }
  const key = cachedKeys.find((item) => item.kid === kid && item.kty === "RSA" && item.use === "sig");
  if (!key) throw new Error("Chave de assinatura Google desconhecida.");
  return key;
}

async function verifyGoogleIdToken(token, clientId) {
  if (typeof token !== "string" || token.length > 12000) {
    throw new Error("Token ausente ou inválido.");
  }
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Formato de token inválido.");

  const header = decodeJsonPart(parts[0]);
  const claims = decodeJsonPart(parts[1]);
  if (header.alg !== "RS256" || typeof header.kid !== "string") {
    throw new Error("Algoritmo ou chave de assinatura inválidos.");
  }

  const jwk = await getGoogleKey(header.kid);
  const publicKey = await crypto.subtle.importKey(
    "jwk",
    jwk,
    { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" },
    false,
    ["verify"],
  );
  const signedContent = new TextEncoder().encode(parts[0] + "." + parts[1]);
  const signature = decodeBase64Url(parts[2]);
  const signatureValid = await crypto.subtle.verify(
    "RSASSA-PKCS1-v1_5",
    publicKey,
    signature,
    signedContent,
  );
  if (!signatureValid) throw new Error("Assinatura Google inválida.");

  const now = Math.floor(Date.now() / 1000);
  if (!GOOGLE_ISSUERS.has(claims.iss)
      || claims.aud !== clientId
      || (claims.azp !== undefined && claims.azp !== clientId)
      || !Number.isFinite(claims.exp)
      || claims.exp <= now
      || !Number.isFinite(claims.iat)
      || claims.iat > now + 60
      || typeof claims.sub !== "string"
      || typeof claims.email !== "string"
      || claims.email_verified !== true) {
    throw new Error("Claims do token Google inválidas ou expiradas.");
  }
  return {
    subject: claims.sub,
    email: claims.email.trim().toLowerCase(),
  };
}

function findShadowUser(email, env) {
  let directory;
  try {
    directory = JSON.parse(env.BRAVO_SHADOW_USERS || "{}");
  } catch {
    throw new Error("Diretório sintético do Shadow está mal configurado.");
  }
  if (!directory || typeof directory !== "object" || Array.isArray(directory)) {
    throw new Error("Diretório sintético do Shadow inválido.");
  }
  const user = directory[email];
  if (!user || user.status !== "Ativo" || typeof user.profile !== "string") return null;
  return user;
}

export default {
  async fetch(request, env) {
    const cors = corsHeaders(request, env);
    const origin = request.headers.get("Origin");
    if (request.method === "OPTIONS") {
      if (!origin || !cors["access-control-allow-origin"]) {
        return json({ detail: "Origem não autorizada." }, 403);
      }
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);
    if (request.method === "GET" && url.pathname === "/api/v1/health") {
      return json({ status: "ok", service: "bravo-shadow-auth-proof", storage: "none" }, 200, cors);
    }

    if (request.method === "GET" && url.pathname === "/api/v1/auth/me") {
      if (!env.GOOGLE_CLIENT_ID) {
        return json({ detail: "Autenticação Google não configurada." }, 503, cors);
      }
      const authorization = request.headers.get("Authorization") || "";
      const match = authorization.match(/^Bearer\s+(.+)$/i);
      if (!match) {
        return json({ detail: "Token de autenticação obrigatório." }, 401, {
          ...cors, "www-authenticate": "Bearer",
        });
      }

      try {
        const identity = await verifyGoogleIdToken(match[1], env.GOOGLE_CLIENT_ID);
        const user = findShadowUser(identity.email, env);
        if (!user) {
          return json({ detail: "Usuário não cadastrado ou inativo no Bravo Shadow." }, 403, cors);
        }
        return json({
          subject: identity.subject,
          email: identity.email,
          profile: user.profile,
          status: user.status,
        }, 200, cors);
      } catch {
        return json({ detail: "Token Google inválido ou não foi possível validar a identidade." }, 401, {
          ...cors, "www-authenticate": "Bearer",
        });
      }
    }

    return json({ detail: "Rota não encontrada." }, 404, cors);
  },
};
