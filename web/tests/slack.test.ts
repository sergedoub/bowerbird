import { describe, expect, it } from "vitest";
import { slackConnectorTestMessage, slackWebhookUrlProblem } from "@/lib/slack";

describe("slack webhook validation", () => {
  it("accepts Slack incoming webhook URLs", () => {
    expect(
      slackWebhookUrlProblem("https://hooks.slack.com/services/T000/B000/secret"),
    ).toBeNull();
  });

  it("rejects non-Slack or non-https URLs", () => {
    expect(slackWebhookUrlProblem("http://hooks.slack.com/services/T/B/C")).toContain("https");
    expect(slackWebhookUrlProblem("https://example.com/services/T/B/C")).toContain("Slack");
  });
});

describe("slack connector test message", () => {
  it("keeps a non-recap test message explicit", () => {
    expect(slackConnectorTestMessage("no recap feed")).toContain("Bowerbird Slack delivery");
  });
});
