export const SLACK_WEBHOOK_SECRET = "SLACK_WEBHOOK_URL";

export function normalizeSlackWebhookUrl(value: string): string {
  return value.trim();
}

export function slackWebhookUrlProblem(value: string): string | null {
  const trimmed = normalizeSlackWebhookUrl(value);
  if (!trimmed) return "Slack webhook URL is required.";
  let url: URL;
  try {
    url = new URL(trimmed);
  } catch {
    return "Slack webhook URL is not a valid URL.";
  }
  if (url.protocol !== "https:") return "Slack webhook URL must use https.";
  if (!["hooks.slack.com", "hooks.slack-gov.com"].includes(url.hostname)) {
    return "Slack webhook URL must come from Slack incoming webhooks.";
  }
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length < 4 || parts[0] !== "services") {
    return "Slack webhook URL must be an incoming webhook URL.";
  }
  return null;
}

export function slackConnectorTestMessage(reason: string): string {
  return [
    "Daily Knowledge Base Recap",
    "",
    "Bowerbird Slack delivery is connected.",
    `Current recap was not posted because ${reason}.`,
  ].join("\n");
}
