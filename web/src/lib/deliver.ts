// Delivery adapters — the connector seam.
//
// An adapter takes the finished recap text and posts it somewhere. Slack (incoming
// webhook) is the launch adapter; Telegram, email, and anything else implement the
// same interface and register in adapterFromEnv. Adapters never re-read the repo or
// reshape the recap — the engine owns content, adapters own transport.

export interface DeliveryAdapter {
  name: string;
  send(text: string): Promise<void>;
}

export class SlackWebhookAdapter implements DeliveryAdapter {
  name = "slack";

  constructor(
    private webhookUrl: string,
    private fetchFn: typeof fetch = fetch,
  ) {}

  async send(text: string): Promise<void> {
    const res = await this.fetchFn(this.webhookUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!res.ok) {
      throw new Error(`Slack webhook responded ${res.status}: ${await res.text()}`);
    }
  }
}

/** The configured adapter, or null when no delivery target is set up. */
export function adapterFromEnv(env = process.env): DeliveryAdapter | null {
  if (env.SLACK_WEBHOOK_URL) return new SlackWebhookAdapter(env.SLACK_WEBHOOK_URL);
  return null;
}
