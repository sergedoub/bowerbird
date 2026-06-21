import type { AccountEntry, TopicEntry } from "./configModel";
import { applyAssignments, type FolderAssignment } from "./folderAssign";
import type { RecapFeed } from "./feed";
import { isFresh } from "./feed";

export const STARTER_ACCOUNTS: AccountEntry[] = [
  {
    handle: "thsottiaux",
    topic: "openai",
    label: "Thibault (OpenAI)",
    offTopic: "skip",
  },
  {
    handle: "bcherny",
    topic: "claude-code",
    label: "Boris (Anthropic)",
    offTopic: "skip",
  },
  {
    handle: "OfficialLoganK",
    topic: "google-ai",
    label: "Logan (Google)",
    offTopic: "skip",
  },
  {
    handle: "santiagomed",
    topic: "xai",
    label: "Santiago (xAI)",
    offTopic: "skip",
  },
];

export interface AuthEnvStatus {
  ok: boolean;
  missing: string[];
}

export type FeedFreshness = "fresh" | "stale" | "missing" | "unknown";
export type SetupTone = "complete" | "pending" | "blocked" | "info";

export interface SetupCheck {
  key: "x" | "repo" | "accounts" | "bookmarks" | "pipeline";
  label: string;
  tone: SetupTone;
  detail: string;
}

export interface HomeSetupState {
  connected: boolean;
  repoReady: boolean;
  accountsConfigured: boolean;
  bookmarksConfigured: boolean;
  sourceConfigured: boolean;
  usable: boolean;
  feedFreshness: FeedFreshness;
  totalAccounts: number;
  totalMappedFolders: number;
  checks: SetupCheck[];
}

export interface HomeSetupInput {
  sessionUsername: string | null;
  auth: AuthEnvStatus;
  repoReady: boolean;
  repoError?: string;
  topics: TopicEntry[];
  accounts: AccountEntry[];
  feed: RecapFeed | null;
  todayUtc: string;
  healthOk?: boolean | null;
}

export interface HomepageConfigPayload {
  topics: TopicEntry[];
  accounts: AccountEntry[];
}

export interface DemoFeedLanePreview {
  key: string;
  label: string;
  totalNew: number;
  notes: string[];
}

export interface DemoFeedPreview {
  generated: string;
  totalNew: number;
  accountLanes: number;
  topicLanes: number;
  lanes: DemoFeedLanePreview[];
}

export function authEnvStatus(env: Record<string, string | undefined>): AuthEnvStatus {
  const missing: string[] = [];
  if (!env.APP_URL) missing.push("APP_URL");
  if (!env.X_CLIENT_ID) missing.push("X_CLIENT_ID");
  if (!env.OWNER_X_USERNAME) missing.push("OWNER_X_USERNAME");
  if (!env.SESSION_SECRET || env.SESSION_SECRET.length < 16) missing.push("SESSION_SECRET");
  return { ok: missing.length === 0, missing };
}

export function hasBookmarkMapping(topics: TopicEntry[]): boolean {
  return topics.some((topic) => topic.folderIds.length > 0);
}

export function countMappedFolders(topics: TopicEntry[]): number {
  return topics.reduce((total, topic) => total + topic.folderIds.length, 0);
}

export function hasAnySource(accounts: AccountEntry[], topics: TopicEntry[]): boolean {
  return accounts.length > 0 || hasBookmarkMapping(topics);
}

export function deriveHomeSetup(input: HomeSetupInput): HomeSetupState {
  const connected = Boolean(input.sessionUsername);
  const accountsConfigured = input.accounts.length > 0;
  const totalMappedFolders = countMappedFolders(input.topics);
  const bookmarksConfigured = totalMappedFolders > 0;
  const sourceConfigured = accountsConfigured || bookmarksConfigured;
  const usable = connected && input.repoReady && sourceConfigured;
  const feedFreshness = feedFreshnessFor(input.feed, input.todayUtc, input.repoReady);

  return {
    connected,
    repoReady: input.repoReady,
    accountsConfigured,
    bookmarksConfigured,
    sourceConfigured,
    usable,
    feedFreshness,
    totalAccounts: input.accounts.length,
    totalMappedFolders,
    checks: [
      {
        key: "x",
        label: "Connect X",
        tone: connected ? "complete" : input.auth.ok ? "pending" : "blocked",
        detail: connected
          ? `Connected as @${input.sessionUsername}`
          : input.auth.ok
            ? "Ready to connect your X account."
            : `Missing ${input.auth.missing.join(", ")}.`,
      },
      {
        key: "repo",
        label: "Connect GitHub repo",
        tone: input.repoReady ? "complete" : "blocked",
        detail: input.repoReady
          ? "Repo config is reachable."
          : (input.repoError ?? "Set GITHUB_REPO and GITHUB_TOKEN."),
      },
      {
        key: "accounts",
        label: "Configure monitored accounts",
        tone: input.repoReady ? (accountsConfigured ? "complete" : "pending") : "blocked",
        detail: accountsConfigured
          ? `${input.accounts.length} account${input.accounts.length === 1 ? "" : "s"} configured.`
          : input.repoReady
            ? "Add accounts to mirror posts and replies."
            : "Connect the repo before account config can be read.",
      },
      {
        key: "bookmarks",
        label: "Map bookmark folders",
        tone: input.repoReady ? (bookmarksConfigured ? "complete" : "pending") : "blocked",
        detail: bookmarksConfigured
          ? `${totalMappedFolders} folder${totalMappedFolders === 1 ? "" : "s"} mapped.`
          : input.repoReady
            ? "Assign at least one X bookmark folder to a topic."
            : "Connect the repo before bookmark mapping can be read.",
      },
      {
        key: "pipeline",
        label: "Pipeline and recap",
        tone: pipelineTone(feedFreshness, input.healthOk),
        detail: pipelineDetail(feedFreshness, input.healthOk),
      },
    ],
  };
}

export function missingStarterAccounts(
  accounts: AccountEntry[],
  starter: AccountEntry[] = STARTER_ACCOUNTS,
): AccountEntry[] {
  const existing = new Set(accounts.map((account) => account.handle.toLowerCase()));
  return starter
    .filter((account) => !existing.has(account.handle.toLowerCase()))
    .map((account) => ({ ...account }));
}

export function mergeStarterAccounts(
  accounts: AccountEntry[],
  starter: AccountEntry[] = STARTER_ACCOUNTS,
): AccountEntry[] {
  return [...accounts, ...missingStarterAccounts(accounts, starter)];
}

export function normalizeAccounts(accounts: AccountEntry[]): AccountEntry[] {
  return accounts.map((account) => {
    const label = account.label?.trim();
    return {
      handle: account.handle.trim().replace(/^@/, ""),
      topic: account.topic.trim(),
      offTopic: account.offTopic === "quarantine" ? "quarantine" : "skip",
      ...(label ? { label } : {}),
    };
  });
}

export function buildHomepageConfigPayload(input: {
  topics: TopicEntry[];
  accounts: AccountEntry[];
  folderAssignments: FolderAssignment[];
}): HomepageConfigPayload {
  return {
    topics: applyAssignments(input.topics, input.folderAssignments),
    accounts: normalizeAccounts(input.accounts),
  };
}

export function buildDemoFeedPreview(feed: RecapFeed | null): DemoFeedPreview | null {
  if (!feed) return null;
  const accountLanes = Object.entries(feed.accounts).map(([key, lane]) => ({
    key,
    label: lane.label,
    totalNew: lane.total_new,
    notes: lane.notes.slice(0, 2).map((note) => firstLine(note.text)),
  }));
  const topicLanes = Object.entries(feed.topics).map(([key, lane]) => ({
    key,
    label: lane.label,
    totalNew: lane.total_new,
    notes: lane.notes.slice(0, 2).map((note) => firstLine(note.text)),
  }));
  return {
    generated: feed.generated,
    totalNew: feed.summary.total_new,
    accountLanes: feed.summary.account_lanes,
    topicLanes: feed.summary.topic_lanes,
    lanes: [...accountLanes, ...topicLanes].slice(0, 4),
  };
}

function feedFreshnessFor(
  feed: RecapFeed | null,
  todayUtc: string,
  repoReady: boolean,
): FeedFreshness {
  if (!repoReady) return "unknown";
  if (!feed) return "missing";
  return isFresh(feed, todayUtc) ? "fresh" : "stale";
}

function pipelineTone(feedFreshness: FeedFreshness, healthOk: boolean | null | undefined): SetupTone {
  if (healthOk) return "complete";
  if (feedFreshness === "fresh") return "complete";
  if (feedFreshness === "unknown") return "blocked";
  return "info";
}

function pipelineDetail(feedFreshness: FeedFreshness, healthOk: boolean | null | undefined): string {
  if (healthOk) return "Latest feed and workflow signals look healthy.";
  if (feedFreshness === "fresh") return "Recap feed is fresh.";
  if (feedFreshness === "stale") return "Recap feed is stale; check pipeline health.";
  if (feedFreshness === "missing") return "No recap feed yet. It appears after the first run.";
  return "Pipeline status unavailable until the repo is reachable.";
}

function firstLine(text: string): string {
  const line = text.split("\n").find((item) => item.trim())?.trim() ?? "";
  return line.length > 140 ? `${line.slice(0, 137)}...` : line;
}
