// Session — a signed, httpOnly cookie carrying the authenticated X username.
//
// Single-tenant: there are no user records; a valid session means "the owner is
// logged in". The X access token ALSO rides in the session cookie (encrypted JWT)
// so /folders can list bookmark folders without a server-side store — the app
// keeps no state of its own.

import { jwtVerify, SignJWT } from "jose";
import { cookies } from "next/headers";

export const SESSION_COOKIE = "bowerbird_session";
const SESSION_TTL_S = 60 * 60 * 24 * 7; // 7 days

export interface Session {
  username: string;
  xAccessToken?: string;
  xUserId?: string;
}

function secretKey(env: Record<string, string | undefined> = process.env): Uint8Array {
  const secret = env.SESSION_SECRET;
  if (!secret || secret.length < 16) {
    throw new Error("SESSION_SECRET must be set (any random string, 16+ chars).");
  }
  return new TextEncoder().encode(secret);
}

export async function sealSession(session: Session, env: Record<string, string | undefined> = process.env): Promise<string> {
  return new SignJWT({ ...session })
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime(`${SESSION_TTL_S}s`)
    .sign(secretKey(env));
}

export async function openSession(
  jwt: string | undefined,
  env: Record<string, string | undefined> = process.env,
): Promise<Session | null> {
  if (!jwt) return null;
  try {
    const { payload } = await jwtVerify(jwt, secretKey(env));
    if (typeof payload.username !== "string") return null;
    return {
      username: payload.username,
      xAccessToken: typeof payload.xAccessToken === "string" ? payload.xAccessToken : undefined,
      xUserId: typeof payload.xUserId === "string" ? payload.xUserId : undefined,
    };
  } catch {
    return null;
  }
}

/** Server-component/route helper: the current session, or null. */
export async function currentSession(): Promise<Session | null> {
  const jar = await cookies();
  return openSession(jar.get(SESSION_COOKIE)?.value);
}

export function sessionCookieOptions() {
  return {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax" as const,
    path: "/",
    maxAge: SESSION_TTL_S,
  };
}
