// Health derivation — feed freshness + latest run per pipeline workflow.
//
// This page exists to catch the silent failure modes: an expired X refresh token
// (pull-bookmarks failing for days), a broken compile, or a recap feed that quietly
// went stale. Pure over fetched inputs so it's unit-testable.

import type { RecapFeed } from "./feed";
import { isFresh } from "./feed";
import type { WorkflowRun } from "./repoClient";

export type FeedStatus = "fresh" | "stale" | "missing";

export interface WorkflowHealth {
  key: string; // workflow file stem, e.g. "pull"
  title: string;
  status: "success" | "failure" | "running" | "never-ran";
  when?: string;
  url?: string;
}

export interface Health {
  feed: FeedStatus;
  feedGenerated?: string;
  totalNew?: number;
  workflows: WorkflowHealth[];
  ok: boolean; // calm header vs attention header
}

/** The pipeline workflows a healthy instance runs; order is display order. */
export const PIPELINE_WORKFLOWS: { file: string; title: string }[] = [
  { file: "pull.yml", title: "Bookmark pull" },
  { file: "account-dump.yml", title: "Account mirror" },
  { file: "compile.yml", title: "Wiki compile + lint" },
  { file: "kb-recap-feed.yml", title: "Recap feed" },
  { file: "slack-recap.yml", title: "Slack recap" },
];

export function deriveHealth(
  feed: RecapFeed | null,
  runs: WorkflowRun[],
  todayUtc: string,
): Health {
  const workflows = PIPELINE_WORKFLOWS.map(({ file, title }) => {
    const latest = runs.find((r) => r.path.endsWith(`/${file}`));
    if (!latest) {
      return { key: file.replace(".yml", ""), title, status: "never-ran" as const };
    }
    const status =
      latest.status !== "completed"
        ? ("running" as const)
        : latest.conclusion === "success"
          ? ("success" as const)
          : ("failure" as const);
    return {
      key: file.replace(".yml", ""),
      title,
      status,
      when: latest.created_at,
      url: latest.html_url,
    };
  });

  const feedStatus: FeedStatus = feed ? (isFresh(feed, todayUtc) ? "fresh" : "stale") : "missing";

  const ok =
    feedStatus === "fresh" &&
    workflows.every((w) => w.status === "success" || w.status === "running" || w.status === "never-ran") &&
    workflows.some((w) => w.status === "success");

  return {
    feed: feedStatus,
    feedGenerated: feed?.generated,
    totalNew: feed?.summary.total_new,
    workflows,
    ok,
  };
}
