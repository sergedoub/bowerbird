import { type NextRequest, NextResponse } from "next/server";
import { authorizeUrl, oauthFlowCookieOptions, pkcePair, xAppForRequest } from "@/lib/xAuth";

// Starts the sign-in-with-X flow: PKCE pair + state ride in short-lived httpOnly
// cookies; the user is sent to X's authorize page for the OWNER'S OWN X app.
export async function GET(req: NextRequest) {
  let app;
  try {
    app = xAppForRequest(req.url, process.env, req.headers);
  } catch (e) {
    return NextResponse.json({ error: String(e instanceof Error ? e.message : e) }, { status: 500 });
  }
  const { verifier, challenge } = await pkcePair();
  const state = crypto.randomUUID();

  const res = NextResponse.redirect(authorizeUrl(app, state, challenge));
  const flowCookie = oauthFlowCookieOptions();
  res.cookies.set("x_oauth_state", state, flowCookie);
  res.cookies.set("x_oauth_verifier", verifier, flowCookie);
  return res;
}
