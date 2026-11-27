import test from "node:test";
import assert from "node:assert/strict";
import worker from "../src/index.js";

const env = {
  GOOGLE_CLIENT_ID: "test-client-id.apps.googleusercontent.com",
  BRAVO_ALLOWED_ORIGIN: "https://bravopinhais.github.io",
  BRAVO_SHADOW_USERS: "{}",
};

test("health endpoint reports isolated non-persistent proof", async () => {
  const request = new Request("https://worker.test/api/v1/health", {
    headers: { Origin: env.BRAVO_ALLOWED_ORIGIN },
  });
  const response = await worker.fetch(request, env);
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
