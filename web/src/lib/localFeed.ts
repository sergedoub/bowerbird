import { readFile } from "node:fs/promises";
import path from "node:path";
import type { RecapFeed } from "./feed";

const RECAP_FEED_PATH = path.join("compile", "recap-feed.json");

export function localRecapFeedPaths(cwd = process.cwd()): string[] {
  return [
    path.join(cwd, RECAP_FEED_PATH),
    path.join(cwd, "..", RECAP_FEED_PATH),
  ].filter((candidate, index, candidates) => candidates.indexOf(candidate) === index);
}

export async function readLocalRecapFeed(cwd = process.cwd()): Promise<RecapFeed | null> {
  for (const candidate of localRecapFeedPaths(cwd)) {
    try {
      const parsed = JSON.parse(await readFile(candidate, "utf8")) as unknown;
      return isRecapFeed(parsed) ? parsed : null;
    } catch (error) {
      if (isNotFound(error)) continue;
      return null;
    }
  }
  return null;
}

function isRecapFeed(value: unknown): value is RecapFeed {
  if (!isRecord(value)) return false;
  if (typeof value.generated !== "string") return false;
  if (typeof value.window_hours !== "number") return false;
  if (!isRecord(value.accounts)) return false;
  if (!isRecord(value.topics)) return false;
  if (!isRecord(value.summary)) return false;
  return (
    typeof value.summary.total_new === "number" &&
    typeof value.summary.account_lanes === "number" &&
    typeof value.summary.topic_lanes === "number"
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function isNotFound(error: unknown): boolean {
  return isRecord(error) && error.code === "ENOENT";
}
