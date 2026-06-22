import { type NextRequest, NextResponse } from "next/server";
import { repoClientFromEnv } from "@/lib/repoClient";
import { setActionsSecret } from "@/lib/secrets";
import { sealSession, SESSION_COOKIE, sessionCookieOptions } from "@/lib/session";
import { exchangeCode, fetchMe, isOwner, xAppForRequest } from "@/lib/xAuth";

const LIVE_INSTANCE_SECRET_NAMES = ["X_CLIENT_ID", "X_BEARER_TOKEN", "X_TOKENS", "GH_PAT"];

// OAuth callback: verify state, exchange the code, enforce the owner gate, seed the
// pipeline's X_TOKENS secret with the captured token, and establish the session.
// Logging in IS the pipeline auth setup — no manual token pasting.
export async function GET(req: NextRequest) {
  const url = new URL(req.url);
  const code = url.searchParams.get("code");
  const state = url.searchParams.get("state");
  const cookieState = req.cookies.get("x_oauth_state")?.value;
  const verifier = req.cookies.get("x_oauth_verifier")?.value;

  if (!code || !state || !verifier || state !== cookieState) {
    return NextResponse.json({ error: "OAuth state mismatch — restart sign-in." }, { status: 400 });
  }

  const owner = process.env.OWNER_X_USERNAME ?? "";
  if (!owner) {
    return NextResponse.json(
      { error: "OWNER_X_USERNAME must be set so only you can sign in." },
      { status: 500 },
    );
  }

  try {
    const tokens = await exchangeCode(xAppForRequest(req.url, process.env, req.headers), code, verifier);
    const me = await fetchMe(tokens.access_token);
    if (!isOwner(me.username, owner)) {
      return NextResponse.json(
        { error: `@${me.username} is not the configured owner of this deploy.` },
        { status: 403 },
      );
    }

    // Seed the pipeline: the token JSON (TokenStore shape) goes into X_TOKENS.
    let seeded = true;
    try {
      const repo = repoClientFromEnv();
      await setActionsSecret(repo, "X_TOKENS", JSON.stringify(tokens));
      const secretNames = new Set(await repo.listActionSecretNames());
      secretNames.add("X_TOKENS");
      if (LIVE_INSTANCE_SECRET_NAMES.every((name) => secretNames.has(name))) {
        await repo.putActionVariable("BOWERBIRD_LIVE_INSTANCE", "true");
      }
    } catch {
      seeded = false; // session still proceeds; /health surfaces the gap
    }

    const res = NextResponse.redirect(new URL(seeded ? "/" : "/?seeding=failed", req.url));
    res.cookies.set(
      SESSION_COOKIE,
      await sealSession({ username: me.username, xAccessToken: tokens.access_token, xUserId: me.id }),
      sessionCookieOptions(),
    );
    res.cookies.delete("x_oauth_state");
    res.cookies.delete("x_oauth_verifier");
    return res;
  } catch (e) {
    return NextResponse.json(
      { error: e instanceof Error ? e.message : String(e) },
      { status: 500 },
    );
  }
}
