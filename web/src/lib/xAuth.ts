// X connector — OAuth2 PKCE flow against the USER'S OWN X developer app, plus the
// authenticated reads the web app needs (identity, bookmark folders).
//
// Sign-in here is double-duty: it authenticates the browser session AND captures the
// exact user-context token the pipeline needs (same app, same scopes). The callback
// route seals that token into the repo's X_TOKENS secret, replacing manual seeding.
// Pure functions over an injectable fetch; routes stay thin.

const AUTHORIZE_URL = "https://x.com/i/oauth2/authorize";
const TOKEN_URL = "https://api.x.com/2/oauth2/token";
const API_BASE = "https://api.x.com/2/";

export const X_SCOPES = "bookmark.read tweet.read users.read offline.access";

export interface XAppConfig {
  clientId: string;
  clientSecret?: string;
  redirectUri: string;
}

export interface XTokens {
  access_token: string;
  refresh_token?: string;
  expires_in?: number;
  scope?: string;
  token_type?: string;
  obtained_at: number; // epoch seconds — what kb.tokens.TokenStore expects
}

type HeaderReader = { get(name: string): string | null };

function firstHeaderValue(value: string | null | undefined): string | undefined {
  return value?.split(",")[0]?.trim() || undefined;
}

export function appUrlForRequest(
  requestUrl: string,
  env: Record<string, string | undefined> = process.env,
  headers?: HeaderReader,
): string {
  const url = new URL(requestUrl);
  const headerHost =
    firstHeaderValue(headers?.get("x-forwarded-host")) ?? firstHeaderValue(headers?.get("host"));
  const headerProto = firstHeaderValue(headers?.get("x-forwarded-proto")) ?? url.protocol.replace(/:$/, "");
  const requestOrigin = headerHost ? `${headerProto}://${headerHost}` : url.origin;
  const configured = env.APP_URL?.replace(/\/$/, "");
  // APP_URL is the canonical OAuth origin. The middleware redirects local
  // localhost traffic to this host before auth starts, so cookies and callback match.
  if (configured) {
    return configured;
  }
  return requestOrigin;
}

export function oauthFlowCookieOptions(env: Record<string, string | undefined> = process.env) {
  return {
    httpOnly: true,
    secure: env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: 600,
  };
}

function b64url(bytes: Uint8Array): string {
  return Buffer.from(bytes)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/** PKCE verifier + S256 challenge. */
export async function pkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: b64url(new Uint8Array(digest)) };
}

export function authorizeUrl(app: XAppConfig, state: string, challenge: string): string {
  const params = new URLSearchParams({
    response_type: "code",
    client_id: app.clientId,
    redirect_uri: app.redirectUri,
    scope: X_SCOPES,
    state,
    code_challenge: challenge,
    code_challenge_method: "S256",
  });
  return `${AUTHORIZE_URL}?${params}`;
}

export async function exchangeCode(
  app: XAppConfig,
  code: string,
  verifier: string,
  fetchFn: typeof fetch = fetch,
  now: () => number = () => Date.now(),
): Promise<XTokens> {
  const form = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: app.redirectUri,
    client_id: app.clientId,
    code_verifier: verifier,
  });
  const headers: Record<string, string> = {
    "Content-Type": "application/x-www-form-urlencoded",
  };
  if (app.clientSecret) {
    headers.Authorization =
      "Basic " + Buffer.from(`${app.clientId}:${app.clientSecret}`).toString("base64");
  }
  const res = await fetchFn(TOKEN_URL, { method: "POST", headers, body: form });
  if (!res.ok) {
    throw new Error(`X token exchange failed: ${res.status} ${await res.text()}`);
  }
  const tokens = (await res.json()) as Omit<XTokens, "obtained_at">;
  // obtained_at is what the pipeline's TokenStore uses for expiry math.
  return { ...tokens, obtained_at: Math.floor(now() / 1000) };
}

async function authedGet<T>(
  path: string,
  accessToken: string,
  fetchFn: typeof fetch,
): Promise<T> {
  const res = await fetchFn(API_BASE + path, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
  if (!res.ok) {
    throw new Error(`X API GET ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export async function fetchMe(
  accessToken: string,
  fetchFn: typeof fetch = fetch,
): Promise<{ id: string; username: string }> {
  const body = await authedGet<{ data: { id: string; username: string } }>(
    "users/me",
    accessToken,
    fetchFn,
  );
  return body.data;
}

export async function listFolders(
  accessToken: string,
  userId: string,
  fetchFn: typeof fetch = fetch,
): Promise<{ id: string; name: string }[]> {
  const body = await authedGet<{ data?: { id: string; name: string }[] }>(
    `users/${encodeURIComponent(userId)}/bookmarks/folders`,
    accessToken,
    fetchFn,
  );
  return body.data ?? [];
}

/**
 * The owner gate: only the configured X account may use this deploy.
 * Comparison is case-insensitive (X usernames are case-preserving but unique
 * case-insensitively).
 */
export function isOwner(username: string, ownerUsername: string): boolean {
  return (
    ownerUsername.trim().length > 0 &&
    username.trim().toLowerCase() === ownerUsername.trim().replace(/^@/, "").toLowerCase()
  );
}

export function xAppFromEnv(
  env: Record<string, string | undefined> = process.env,
  appUrlOverride?: string,
): XAppConfig {
  const clientId = env.X_CLIENT_ID;
  const appUrl = appUrlOverride ?? env.APP_URL;
  if (!clientId || !appUrl) {
    throw new Error("X_CLIENT_ID and APP_URL must be set for sign-in with X.");
  }
  return {
    clientId,
    clientSecret: env.X_CLIENT_SECRET || undefined,
    redirectUri: `${appUrl.replace(/\/$/, "")}/api/auth/callback`,
  };
}

export function xAppForRequest(
  requestUrl: string,
  env: Record<string, string | undefined> = process.env,
  headers?: HeaderReader,
): XAppConfig {
  return xAppFromEnv(env, appUrlForRequest(requestUrl, env, headers));
}
