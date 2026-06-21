import { describe, expect, it } from "vitest";
import { validateConfig } from "@/lib/configModel";
import {
  authEnvStatus,
  buildDemoFeedPreview,
  buildHomepageConfigPayload,
  deriveHomeSetup,
  mergeStarterAccounts,
  missingStarterAccounts,
} from "@/lib/home";

const TODAY = "2026-06-18";
const AUTH_OK = {
  APP_URL: "http://bowerbird.localhost:3000",
  X_CLIENT_ID: "client",
  OWNER_X_USERNAME: "owner",
  SESSION_SECRET: "1234567890123456",
};

function feed(generated = TODAY) {
  return {
    generated,
    window_hours: 24,
    accounts: {
      bcherny: {
        label: "Boris (Anthropic)",
        total_new: 2,
        notes: [
          {
            date: TODAY,
            file: "wiki/claude-code/sources/example.md",
            text: "Claude Code shipped a new agent workflow.\nSecond paragraph.",
          },
        ],
      },
    },
    topics: {},
    summary: { total_new: 2, account_lanes: 1, topic_lanes: 0 },
  };
}

describe("authEnvStatus", () => {
  it("reports the exact missing X/session env vars", () => {
    expect(authEnvStatus({ APP_URL: "x", SESSION_SECRET: "short" })).toEqual({
      ok: false,
      missing: ["X_CLIENT_ID", "OWNER_X_USERNAME", "SESSION_SECRET"],
    });
  });

  it("accepts the env needed to connect with X", () => {
    expect(authEnvStatus(AUTH_OK).ok).toBe(true);
  });
});

describe("deriveHomeSetup", () => {
  it("disconnected: repo can be ready, but X blocks usability", () => {
    const setup = deriveHomeSetup({
      sessionUsername: null,
      auth: authEnvStatus(AUTH_OK),
      repoReady: true,
      topics: [],
      accounts: [],
      feed: null,
      todayUtc: TODAY,
    });
    expect(setup.connected).toBe(false);
    expect(setup.usable).toBe(false);
    expect(setup.checks.find((check) => check.key === "x")?.tone).toBe("pending");
  });

  it("connected-empty: still needs at least one source", () => {
    const setup = deriveHomeSetup({
      sessionUsername: "owner",
      auth: authEnvStatus(AUTH_OK),
      repoReady: true,
      topics: [],
      accounts: [],
      feed: feed(),
      todayUtc: TODAY,
    });
    expect(setup.connected).toBe(true);
    expect(setup.sourceConfigured).toBe(false);
    expect(setup.usable).toBe(false);
  });

  it("connected with accounts is usable", () => {
    const setup = deriveHomeSetup({
      sessionUsername: "owner",
      auth: authEnvStatus(AUTH_OK),
      repoReady: true,
      topics: [],
      accounts: [{ handle: "bcherny", topic: "claude-code", offTopic: "skip" }],
      feed: feed(),
      todayUtc: TODAY,
    });
    expect(setup.accountsConfigured).toBe(true);
    expect(setup.bookmarksConfigured).toBe(false);
    expect(setup.usable).toBe(true);
  });

  it("connected with a bookmark mapping is usable without accounts", () => {
    const setup = deriveHomeSetup({
      sessionUsername: "owner",
      auth: authEnvStatus(AUTH_OK),
      repoReady: true,
      topics: [{ name: "research", folderIds: ["111"] }],
      accounts: [],
      feed: feed(),
      todayUtc: TODAY,
    });
    expect(setup.accountsConfigured).toBe(false);
    expect(setup.bookmarksConfigured).toBe(true);
    expect(setup.usable).toBe(true);
  });

  it("missing GitHub env blocks repo and source checks", () => {
    const setup = deriveHomeSetup({
      sessionUsername: "owner",
      auth: authEnvStatus(AUTH_OK),
      repoReady: false,
      repoError: "GITHUB_REPO and GITHUB_TOKEN must be set",
      topics: [],
      accounts: [],
      feed: null,
      todayUtc: TODAY,
    });
    expect(setup.repoReady).toBe(false);
    expect(setup.usable).toBe(false);
    expect(setup.checks.find((check) => check.key === "repo")?.tone).toBe("blocked");
  });
});

describe("starter accounts", () => {
  it("adds missing defaults without duplicating existing handles", () => {
    const existing = [{ handle: "BCherny", topic: "custom", offTopic: "skip" as const }];
    const missing = missingStarterAccounts(existing);
    expect(missing.some((account) => account.handle === "bcherny")).toBe(false);
    const merged = mergeStarterAccounts(existing);
    expect(merged.filter((account) => account.handle.toLowerCase() === "bcherny")).toHaveLength(1);
    expect(merged).toHaveLength(4);
  });
});

describe("buildDemoFeedPreview", () => {
  it("summarizes real recap lanes for the disconnected homepage", () => {
    expect(buildDemoFeedPreview(feed())).toEqual({
      generated: TODAY,
      totalNew: 2,
      accountLanes: 1,
      topicLanes: 0,
      lanes: [
        {
          key: "bcherny",
          label: "Boris (Anthropic)",
          totalNew: 2,
          notes: ["Claude Code shipped a new agent workflow."],
        },
      ],
    });
  });

  it("returns null when there is no feed", () => {
    expect(buildDemoFeedPreview(null)).toBeNull();
  });
});

describe("buildHomepageConfigPayload", () => {
  it("preserves staged accounts and visible bookmark assignments", () => {
    const payload = buildHomepageConfigPayload({
      topics: [
        { name: "marketing", folderIds: ["111", "999"] },
        { name: "ai", folderIds: ["222"] },
      ],
      accounts: [{ handle: "@bcherny", topic: "claude-code", label: " Boris ", offTopic: "skip" }],
      folderAssignments: [
        { folderId: "111", topic: "ai" },
        { folderId: "222", topic: "new-topic" },
      ],
    });
    expect(payload.accounts).toEqual([
      { handle: "bcherny", topic: "claude-code", label: "Boris", offTopic: "skip" },
    ]);
    expect(payload.topics).toEqual([
      { name: "marketing", folderIds: ["999"] },
      { name: "ai", folderIds: ["111"] },
      { name: "new-topic", folderIds: ["222"] },
    ]);
  });

  it("allows inline topic auto-create through existing validation", () => {
    const payload = buildHomepageConfigPayload({
      topics: [],
      accounts: [],
      folderAssignments: [{ folderId: "111", topic: "new-topic" }],
    });
    expect(() => validateConfig(payload)).not.toThrow();
  });
});
