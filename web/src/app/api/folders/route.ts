import { NextResponse } from "next/server";
import { currentSession } from "@/lib/session";
import { listFolders } from "@/lib/xAuth";

// The signed-in owner's bookmark folders, via the X token riding in the session.
export async function GET() {
  const session = await currentSession();
  if (!session) {
    return NextResponse.json({ error: "sign in first" }, { status: 401 });
  }
  if (!session.xAccessToken || !session.xUserId) {
    return NextResponse.json(
      { error: "session has no X token — sign in with X again" },
      { status: 401 },
    );
  }
  try {
    return NextResponse.json({ folders: await listFolders(session.xAccessToken, session.xUserId) });
  } catch (e) {
    // Most common cause: the ~2h X access token expired; a fresh sign-in fixes it.
    return NextResponse.json(
      { error: `${e instanceof Error ? e.message : e} — try signing in again` },
      { status: 502 },
    );
  }
}
