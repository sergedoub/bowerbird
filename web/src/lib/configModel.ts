// Config model — parse, validate, and serialize the instance's TOML configs.
//
// The most safety-critical module in the app: a bad write here corrupts the user's
// pipeline config. Validation mirrors the Python loaders (kb.config): every topic has
// >= 1 folder id, no folder feeds two topics, handles+topics required, known off_topic
// policies, no duplicate handles. Serialization matches the `bowerbird init` writers
// so files round-trip cleanly between the wizard, this editor, and human edits.

import { parse as parseToml } from "smol-toml";

export interface TopicEntry {
  name: string;
  folderIds: string[];
}

export interface AccountEntry {
  handle: string;
  topic: string;
  offTopic: "skip" | "quarantine";
  label?: string;
}

export class ConfigValidationError extends Error {
  constructor(public readonly problems: string[]) {
    super(problems.join("; "));
  }
}

const SLUG = /^[a-z0-9][a-z0-9-_]*$/;
const HANDLE = /^[A-Za-z0-9_]{1,15}$/;
const FOLDER_ID = /^\d+$/;

// ---------- topics ----------

export function parseTopics(toml: string): TopicEntry[] {
  const data = parseToml(toml) as { topics?: Record<string, { folder_ids?: unknown }> };
  const raw = data.topics ?? {};
  return Object.entries(raw).map(([name, body]) => ({
    name,
    folderIds: Array.isArray(body.folder_ids) ? body.folder_ids.map(String) : [],
  }));
}

export function validateTopics(topics: TopicEntry[]): string[] {
  const problems: string[] = [];
  const seenFolder = new Map<string, string>();
  const seenName = new Set<string>();
  for (const t of topics) {
    if (!SLUG.test(t.name)) {
      problems.push(`topic name '${t.name}' must be a lowercase slug (a-z, 0-9, -, _)`);
    }
    if (seenName.has(t.name)) problems.push(`duplicate topic '${t.name}'`);
    seenName.add(t.name);
    if (t.folderIds.length === 0) problems.push(`topic '${t.name}' has no folder ids`);
    for (const fid of t.folderIds) {
      if (!FOLDER_ID.test(fid)) {
        problems.push(`folder id '${fid}' in topic '${t.name}' must be numeric`);
      }
      const other = seenFolder.get(fid);
      if (other) problems.push(`folder ${fid} is mapped to both '${other}' and '${t.name}'`);
      seenFolder.set(fid, t.name);
    }
  }
  return problems;
}

export function serializeTopics(topics: TopicEntry[]): string {
  const lines = ["# Bookmark folders -> wiki topics. Managed by the Bowerbird web app.", ""];
  for (const t of topics) {
    lines.push(`[topics.${t.name}]`);
    lines.push(`folder_ids = [${t.folderIds.map((i) => `"${i}"`).join(", ")}]`);
    lines.push("");
  }
  return lines.join("\n");
}

// ---------- accounts ----------

export function parseAccounts(toml: string): AccountEntry[] {
  const data = parseToml(toml) as { handles?: Record<string, unknown>[] };
  return (data.handles ?? []).map((h) => ({
    handle: String(h.handle ?? "").replace(/^@/, ""),
    topic: String(h.topic ?? ""),
    offTopic: (String(h.off_topic ?? "skip") || "skip") as AccountEntry["offTopic"],
    label: h.label ? String(h.label) : undefined,
  }));
}

export function validateAccounts(accounts: AccountEntry[]): string[] {
  const problems: string[] = [];
  const seen = new Set<string>();
  for (const a of accounts) {
    if (!HANDLE.test(a.handle)) {
      problems.push(`handle '${a.handle}' is not a valid X username`);
    }
    if (!SLUG.test(a.topic)) {
      problems.push(`topic '${a.topic}' for @${a.handle} must be a lowercase slug`);
    }
    if (!["skip", "quarantine"].includes(a.offTopic)) {
      problems.push(`unknown off_topic policy '${a.offTopic}' for @${a.handle}`);
    }
    const key = a.handle.toLowerCase();
    if (seen.has(key)) problems.push(`duplicate handle '@${a.handle}'`);
    seen.add(key);
    if (a.label !== undefined && /[\n"]/.test(a.label)) {
      problems.push(`label for @${a.handle} must not contain quotes or newlines`);
    }
  }
  return problems;
}

export function serializeAccounts(accounts: AccountEntry[]): string {
  const lines = ["# X accounts to mirror. Managed by the Bowerbird web app.", ""];
  for (const a of accounts) {
    lines.push("[[handles]]");
    lines.push(`handle = "${a.handle}"`);
    lines.push(`topic = "${a.topic}"`);
    if (a.label) lines.push(`label = "${a.label}"`);
    lines.push(`off_topic = "${a.offTopic}"`);
    lines.push("");
  }
  return lines.join("\n");
}

// ---------- combined ----------

export interface InstanceConfig {
  topics: TopicEntry[];
  accounts: AccountEntry[];
}

/** Validate everything; throws ConfigValidationError listing every problem at once. */
export function validateConfig(config: InstanceConfig): void {
  const problems = [...validateTopics(config.topics), ...validateAccounts(config.accounts)];
  if (problems.length > 0) throw new ConfigValidationError(problems);
}
