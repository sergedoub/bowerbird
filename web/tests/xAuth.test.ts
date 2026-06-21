// X connector: PKCE, authorize URL, code exchange (token shape the pipeline expects),
// owner gate, folder listing. Fake fetch throughout.
import { describe, expect, it } from "vitest";
import {
  appUrlForRequest,
  authorizeUrl,
  exchangeCode,
  fetchMe,
  isOwner,
  listFolders,
  oauthFlowCookieOptions,
  pkcePair,
  X_SCOPES,
  xAppForRequest,
  xAppFromEnv,
} from "@/lib/xAuth";

const app = {
  clientId: "cid",
  clientSecret: "csecret",
  redirectUri: "https://app.example/api/auth/callback",
};

describe("pkcePair", () => {
  it("produces a url-safe verifier and S256 challenge", async () => {
    const { verifier, challenge } = await pkcePair();
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{40,}$/);
    expect(challenge).toMatch(/^[A-Za-z0-9_-]{40,}$/);
    expect(challenge).not.toBe(verifier);
  });
});

describe("authorizeUrl", () => {
  it("carries client id, redirect, scopes, state, and challenge", () => {
    const url = new URL(authorizeUrl(app, "state-1", "chal"));
    expect(url.origin + url.pathname).toBe("https://x.com/i/oauth2/authorize");
    expect(url.searchParams.get("client_id")).toBe("cid");
    expect(url.searchParams.get("redirect_uri")).toBe(app.redirectUri);
    expect(url.searchParams.get("scope")).toBe(X_SCOPES);
    expect(url.searchParams.get("state")).toBe("state-1");
    expect(url.searchParams.get("code_challenge")).toBe("chal");
    expect(url.searchParams.get("code_challenge_method")).toBe("S256");
  });
});

describe("request-aware app config", () => {
  it("uses APP_URL in development as the canonical callback host", () => {
    const env = {
      NODE_ENV: "development",
      X_CLIENT_ID: "cid",
      APP_URL: "http://bowerbird.localhost:3000",
    };

    expect(appUrlForRequest("http://localhost:3000/api/auth/login", env)).toBe(
      "http://bowerbird.localhost:3000",
    );
    expect(xAppForRequest("http://localhost:3000/api/auth/login", env).redirectUri).toBe(
      "http://bowerbird.localhost:3000/api/auth/callback",
    );
  });

  it("falls back to the browser Host header when APP_URL is not configured", () => {
    const env = {
      NODE_ENV: "development",
      X_CLIENT_ID: "cid",
    };
    const headers = new Headers({ host: "bowerbird.localhost:3000" });

    expect(appUrlForRequest("http://localhost:3000/api/auth/login", env, headers)).toBe(
      "http://bowerbird.localhost:3000",
    );
  });

  it("uses APP_URL in production", () => {
    const env = {
      NODE_ENV: "production",
      X_CLIENT_ID: "cid",
      APP_URL: "https://bowerbird.example",
    };

    expect(appUrlForRequest("http://internal:3000/api/auth/login", env)).toBe(
      "https://bowerbird.example",
    );
    expect(xAppFromEnv(env).redirectUri).toBe("https://bowerbird.example/api/auth/callback");
  });

  it("does not require secure OAuth flow cookies during local HTTP setup", () => {
    expect(oauthFlowCookieOptions({ NODE_ENV: "development" }).secure).toBe(false);
    expect(oauthFlowCookieOptions({ NODE_ENV: "production" }).secure).toBe(true);
  });
});

describe("exchangeCode", () => {
  it("posts the PKCE form with basic auth and stamps obtained_at", async () => {
    let captured: { url: string; init?: RequestInit } | undefined;
    const fetchFn = (async (url: any, init?: RequestInit) => {
      captured = { url: String(url), init };
      return Response.json({
        access_token: "at",
        refresh_token: "rt",
        expires_in: 7200,
      });
    }) as typeof fetch;

    const tokens = await exchangeCode(app, "the-code", "the-verifier", fetchFn, () => 1750000000000);
    expect(tokens).toEqual({
      access_token: "at",
      refresh_token: "rt",
      expires_in: 7200,
      obtained_at: 1750000000, // seconds — kb.tokens.TokenStore expiry math
    });
    const body = String(captured?.init?.body);
    expect(body).toContain("grant_type=authorization_code");
    expect(body).toContain("code_verifier=the-verifier");
    expect((captured?.init?.headers as any).Authorization).toMatch(/^Basic /);
  });

  it("throws with status on failure", async () => {
    const fetchFn = (async () => new Response("nope", { status: 400 })) as typeof fetch;
    await expect(exchangeCode(app, "c", "v", fetchFn)).rejects.toThrow("400");
  });
});

describe("identity + folders", () => {
  it("fetchMe returns id and username", async () => {
    const fetchFn = (async () =>
      Response.json({ data: { id: "42", username: "alice" } })) as typeof fetch;
    expect(await fetchMe("at", fetchFn)).toEqual({ id: "42", username: "alice" });
  });

  it("listFolders returns the folder array (empty when none)", async () => {
    const fetchFn = (async (url: any) => {
      expect(String(url)).toContain("users/42/bookmarks/folders");
      return Response.json({ data: [{ id: "9", name: "marketing" }] });
    }) as typeof fetch;
    expect(await listFolders("at", "42", fetchFn)).toEqual([{ id: "9", name: "marketing" }]);

    const empty = (async () => Response.json({})) as typeof fetch;
    expect(await listFolders("at", "42", empty)).toEqual([]);
  });
});

describe("isOwner — the gate that keeps a deploy single-tenant", () => {
  it("accepts the owner case-insensitively, with or without @", () => {
    expect(isOwner("Alice", "alice")).toBe(true);
    expect(isOwner("alice", "@Alice")).toBe(true);
  });
  it("rejects anyone else, and rejects everything when unconfigured", () => {
    expect(isOwner("mallory", "alice")).toBe(false);
    expect(isOwner("anyone", "")).toBe(false);
    expect(isOwner("anyone", "   ")).toBe(false);
  });
});
