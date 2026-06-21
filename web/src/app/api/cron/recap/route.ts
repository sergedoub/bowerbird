import { NextResponse } from "next/server";
import { adapterFromEnv } from "@/lib/deliver";
import { todayUtc } from "@/lib/feed";
import { buildRecap, quietMessage, shouldDeliver } from "@/lib/recap";
import { repoClientFromEnv } from "@/lib/repoClient";
import { summarizerFromEnv } from "@/lib/summarizer";

export const dynamic = "force-dynamic";
export const maxDuration = 120; // LLM synthesis can take a moment

// The daily recap delivery: fetch feed -> guards -> synthesize -> adapter.send.
// Triggered by the platform cron (vercel.json) or manually with the same secret.
export async function GET(req: Request) {
  const secret = process.env.CRON_SECRET;
  if (secret && req.headers.get("authorization") !== `Bearer ${secret}`) {
    return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  }

  const adapter = adapterFromEnv();
  if (!adapter) {
    return NextResponse.json(
      { delivered: false, reason: "no delivery adapter configured (set SLACK_WEBHOOK_URL)" },
      { status: 200 },
    );
  }

  const repo = repoClientFromEnv();
  const [feed, modelSettings] = await Promise.all([
    repo.getRecapFeed(),
    repo.getModelSettings(),
  ]);
  const decision = shouldDeliver(feed, todayUtc(), {
    quietMessageOnEmpty: process.env.RECAP_QUIET_MESSAGE === "true",
  });
  if (!decision.deliver) {
    console.log(`recap skipped: ${decision.reason}`);
    return NextResponse.json({ delivered: false, reason: decision.reason });
  }

  const result = decision.quiet
    ? { text: quietMessage(feed!), synthesized: false }
    : await buildRecap(feed!, summarizerFromEnv(process.env, modelSettings));

  await adapter.send(result.text);
  return NextResponse.json({
    delivered: true,
    adapter: adapter.name,
    synthesized: result.synthesized,
    quiet: decision.quiet,
  });
}
