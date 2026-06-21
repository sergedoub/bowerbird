// Delivery adapters: Slack webhook posts the right body and surfaces failures;
// env selection picks the configured adapter.
import { describe, expect, it } from "vitest";
import { adapterFromEnv, SlackWebhookAdapter } from "@/lib/deliver";

describe("SlackWebhookAdapter", () => {
  it("POSTs {text} as JSON to the webhook", async () => {
    let captured: { url: string; init?: RequestInit } | undefined;
    const fetchFn = (async (url: any, init?: RequestInit) => {
      captured = { url: String(url), init };
      return new Response("ok");
    }) as typeof fetch;

    await new SlackWebhookAdapter("https://hooks.slack.com/services/X", fetchFn).send("recap!");
    expect(captured?.url).toBe("https://hooks.slack.com/services/X");
    expect(JSON.parse(String(captured?.init?.body))).toEqual({ text: "recap!" });
  });

  it("throws on a non-2xx response so the cron run fails visibly", async () => {
    const fetchFn = (async () => new Response("no_service", { status: 404 })) as typeof fetch;
    await expect(
      new SlackWebhookAdapter("https://hooks.slack.com/services/X", fetchFn).send("x"),
    ).rejects.toThrow("404");
  });
});

describe("adapterFromEnv", () => {
  it("returns slack when configured, null when nothing is", () => {
    expect(adapterFromEnv({ SLACK_WEBHOOK_URL: "https://hooks.slack.com/x" } as any)?.name).toBe(
      "slack",
    );
    expect(adapterFromEnv({} as any)).toBeNull();
  });
});
