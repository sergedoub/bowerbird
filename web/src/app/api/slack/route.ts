import { NextResponse } from "next/server";
import { SlackWebhookAdapter } from "@/lib/deliver";
import { todayUtc } from "@/lib/feed";
import { buildRecap, quietMessage, shouldDeliver } from "@/lib/recap";
import { repoClientFromEnv } from "@/lib/repoClient";
import { setActionsSecret } from "@/lib/secrets";
import {
  normalizeSlackWebhookUrl,
  SLACK_WEBHOOK_SECRET,
  slackConnectorTestMessage,
  slackWebhookUrlProblem,
} from "@/lib/slack";
import { summarizerFromEnv } from "@/lib/summarizer";
import { currentSession } from "@/lib/session";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

export async function GET() {
  if (!(await currentSession())) {
    return NextResponse.json({ error: "sign in first" }, { status: 401 });
  }
  const repo = repoClientFromEnv();
  const names = await repo.listActionSecretNames();
  return NextResponse.json({
    configured: names.includes(SLACK_WEBHOOK_SECRET),
    localConfigured: Boolean(process.env.SLACK_WEBHOOK_URL),
    secretName: SLACK_WEBHOOK_SECRET,
  });
}

export async function POST(req: Request) {
  if (!(await currentSession())) {
    return NextResponse.json({ error: "sign in first" }, { status: 401 });
  }
  const body = (await req.json().catch(() => ({}))) as { webhookUrl?: string };
  const webhookUrl = normalizeSlackWebhookUrl(body.webhookUrl ?? "");
  const problem = slackWebhookUrlProblem(webhookUrl);
  if (problem) {
    return NextResponse.json({ error: problem }, { status: 422 });
  }

  const repo = repoClientFromEnv();
  const [feed, modelSettings] = await Promise.all([
    repo.getRecapFeed(),
    repo.getModelSettings(),
  ]);
  const decision = shouldDeliver(feed, todayUtc(), { quietMessageOnEmpty: true });
  const recap =
    decision.deliver && decision.quiet
      ? { text: quietMessage(feed!), kind: "quiet" }
      : decision.deliver
        ? {
            text: (await buildRecap(feed!, summarizerFromEnv(process.env, modelSettings))).text,
            kind: "recap",
          }
        : { text: slackConnectorTestMessage(decision.reason), kind: "connection-test" };

  await new SlackWebhookAdapter(webhookUrl).send(recap.text);
  await setActionsSecret(repo, SLACK_WEBHOOK_SECRET, webhookUrl);

  return NextResponse.json({
    configured: true,
    posted: true,
    postKind: recap.kind,
    secretName: SLACK_WEBHOOK_SECRET,
  });
}
