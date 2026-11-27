import test from "node:test";
import assert from "node:assert/strict";
import { generateKeyPairSync, sign as signBytes } from "node:crypto";
import worker from "../src/index.js";

const env = {
  GOOGLE_CLIENT_ID: "test-client-id.apps.googleusercontent.com",
  BRAVO_ALLOWED_ORIGIN: "https://bravopinhais.github.io",
  BRAVO_SHADOW_USERS: "{}",
};

const { privateKey, publicKey } = generateKeyPairSync("rsa", {
  modulusLength: 2048,
  publicKeyEncoding: { type: "spki", format: "pem" },
  privateKeyEncoding: { type: "pkcs8", format: "pem" },
});
const publicJwk = {
  ...createPublicJwk(publicKey),
  kid: "bravo-test-key",
  use: "sig",
  alg: "RS256",
};

function createPublicJwk(pem) {
  const { createPublicKey } = awaitlessCrypto();
  return createPublicKey(pem).export({ format: "jwk" });
}

// Isola a consulta de certificados Google: nenhum request externo é realizado.
const originalFetch = globalThis.fetch;
globalThis.fetch = async (input) => {
  if (String(input) !== "https://www.googleapis.com/oauth2/v3/certs") {
    throw new Error("Request externo inesperado no teste.");
  }
  return new Response(JSON.stringify({ keys: [publicJwk] }), {
    status: 200,
    headers: { "content-type": "application/json", "cache-control": "max-age=300" },
  });
};

function awaitlessCrypto() {
  return { createPublicKey: (pem) => {
    // A chave pública é derivada apenas da chave privada sintética criada no teste.
    return requireCryptoCreatePublicKey(pem);
  }};
}

import { createPublicKey as requireCryptoCreatePublicKey } from "node:crypto";

function base64url(value) {
  return Buffer.from(typeof value === "string" ? value : JSON.stringify(value)).toString("base64url");
}

function makeToken(overrides = {}, options = {}) {
  const now = Math.floor(Date.now() / 1000);
  const header = { alg: "RS256", typ: "JWT", kid: "bravo-test-key" };
  const claims = {
    iss: "https://accounts.google.com",
    aud: env.GOOGLE_CLIENT_ID,
    sub: "google-subject-synthetic-123",
    email: "usuario-teste@example.com",
    email_verified: true,
    iat: now,
    exp: now + 300,
    ...overrides,
  };
  const unsigned = base64url(header) + "." + base64url(claims);
  const signature = signBytes("RSA-SHA256", Buffer.from(unsigned), privateKey);
  const finalSignature = options.tamper
    ? Buffer.from(signature).map((byte, index) => index === 0 ? byte ^ 1 : byte)
    : signature;
  return unsigned + "." + Buffer.from(finalSignature).toString("base64url");
}

async function authRequest(token, runtimeEnv = env) {
  return worker.fetch(new Request("https://worker.test/api/v1/auth/me", {
    headers: { Authorization: "Bearer " + token, Origin: env.BRAVO_ALLOWED_ORIGIN },
  }), runtimeEnv);
}

test("health endpoint reports isolated non-persistent proof", async () => {
  const response = await worker.fetch(new Request("https://worker.test/api/v1/health", {
    headers: { Origin: env.BRAVO_ALLOWED_ORIGIN },
  }), env);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get("access-control-allow-origin"), env.BRAVO_ALLOWED_ORIGIN);
  assert.deepEqual(await response.json(), {
    status: "ok",
    service: "bravo-shadow-auth-proof",
    storage: "none",
  });
});

test("preflight allows only the configured origin", async () => {
  const allowed = await worker.fetch(new Request("https://worker.test/api/v1/auth/me", {
    method: "OPTIONS",
    headers: { Origin: env.BRAVO_ALLOWED_ORIGIN },
  }), env);
  assert.equal(allowed.status, 204);
  assert.equal(allowed.headers.get("access-control-allow-origin"), env.BRAVO_ALLOWED_ORIGIN);

  const denied = await worker.fetch(new Request("https://worker.test/api/v1/auth/me", {
    method: "OPTIONS",
    headers: { Origin: "https://example.invalid" },
  }), env);
  assert.equal(denied.status, 403);
});

test("auth endpoint rejects requests without a bearer token", async () => {
  const response = await worker.fetch(new Request("https://worker.test/api/v1/auth/me"), env);
  assert.equal(response.status, 401);
  assert.equal(response.headers.get("www-authenticate"), "Bearer");
});

test("unknown routes return 404", async () => {
  const response = await worker.fetch(new Request("https://worker.test/not-found"), env);
  assert.equal(response.status, 404);
});

test("valid Google token grants only a synthetic active registered user", async () => {
  const testEnv = {
    ...env,
    BRAVO_SHADOW_USERS: JSON.stringify({
      "usuario-teste@example.com": { profile: "Operador", status: "Ativo" },
    }),
  };
  const response = await authRequest(makeToken(), testEnv);
  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    subject: "google-subject-synthetic-123",
    email: "usuario-teste@example.com",
    profile: "Operador",
    status: "Ativo",
  });
});

test("valid Google token is denied when the email is not registered", async () => {
  const response = await authRequest(makeToken(), env);
  assert.equal(response.status, 403);
});

test("valid Google token is denied for an inactive synthetic user", async () => {
  const testEnv = {
    ...env,
    BRAVO_SHADOW_USERS: JSON.stringify({
      "usuario-teste@example.com": { profile: "Operador", status: "Inativo" },
    }),
  };
  const response = await authRequest(makeToken(), testEnv);
  assert.equal(response.status, 403);
});

test("tampered Google token signature is rejected", async () => {
  const testEnv = {
    ...env,
    BRAVO_SHADOW_USERS: JSON.stringify({
      "usuario-teste@example.com": { profile: "Operador", status: "Ativo" },
    }),
  };
  const response = await authRequest(makeToken({}, { tamper: true }), testEnv);
  assert.equal(response.status, 401);
});

test("wrong audience is rejected", async () => {
  const response = await authRequest(makeToken({ aud: "another-client-id" }), env);
  assert.equal(response.status, 401);
});

test("unverified email is rejected", async () => {
  const response = await authRequest(makeToken({ email_verified: false }), env);
  assert.equal(response.status, 401);
});

test("expired Google token is rejected", async () => {
  const now = Math.floor(Date.now() / 1000);
  const response = await authRequest(makeToken({ iat: now - 600, exp: now - 1 }), env);
  assert.equal(response.status, 401);
});

test.after(() => {
  globalThis.fetch = originalFetch;
});
