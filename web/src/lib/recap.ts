// Recap engine — feed in, one deliverable message out.
//
// Pure core: the guards (freshness, zero-new-content) and the synthesis prompt are
// plain functions; the LLM is injected as (prompt) => text so everything is testable
// offline. The rules mirror docs/slack-recap.md: never post a stale feed, quiet days
// are quiet, one message covering every lane, synthesis not dump.

import type { RecapFeed } from "./feed";
import { isFresh } from "./feed";

export type Decision =
  | { deliver: true; quiet: boolean }
  | { deliver: false; reason: string };

/**
 * The delivery guard. A stale feed is never posted — posting old notes as new is
 * worse than posting nothing. Zero-new days deliver a quiet message only when
 * `quietMessageOnEmpty` is set; otherwise they skip.
 */
export function shouldDeliver(
  feed: RecapFeed | null,
  todayUtc: string,
  opts: { quietMessageOnEmpty: boolean },
): Decision {
  if (!feed) return { deliver: false, reason: "no recap feed in the repo yet" };
  if (!isFresh(feed, todayUtc)) {
    return {
      deliver: false,
      reason: `stale feed: generated ${feed.generated}, today is ${todayUtc}`,
    };
  }
  if (feed.summary.total_new === 0) {
    if (opts.quietMessageOnEmpty) return { deliver: true, quiet: true };
    return { deliver: false, reason: "no new notes in the window" };
  }
  return { deliver: true, quiet: false };
}

export function quietMessage(feed: RecapFeed): string {
  return `Daily Knowledge Base Recap — ${feed.generated}\n\nA quiet day: no new source notes in the last ${feed.window_hours}h.`;
}

/** The synthesis instruction: lanes in, one organized recap out. */
export function synthesisPrompt(feed: RecapFeed): string {
  const lanes: string[] = [];
  for (const [group, label] of [
    ["accounts", "Accounts"],
    ["topics", "Topics"],
  ] as const) {
    for (const [key, lane] of Object.entries(feed[group])) {
      const notes = lane.notes
        .map((n) => `  - (${n.date}) ${n.text.replace(/\n+/g, " ").slice(0, 600)}`)
        .join("\n");
      lanes.push(`${label} / ${lane.label} (${key}): ${lane.total_new} new note(s)\n${notes}`);
    }
  }
  return [
    "You write a daily knowledge-base recap message. Below are today's new source",
    "notes, grouped into lanes (accounts the user mirrors, and topics).",
    "",
    "Write ONE recap message:",
    "- Start with the heading line: Daily Knowledge Base Recap — " + feed.generated,
    "- One section per lane, keeping the lane's display label as a bold heading",
    '- Under each lane: a concise synthesis of the important themes (2-4 bullets), not a dump of every note',
    "- Preserve specific numbers, names, and claims exactly; do not add your own advice",
    "- Plain text with minimal markdown (bold headings and dashes only), suitable for Slack",
    "",
    "Lanes:",
    "",
    lanes.join("\n\n"),
  ].join("\n");
}

export interface RecapResult {
  text: string;
  synthesized: boolean; // false = mechanical fallback (no LLM configured/available)
}

/**
 * Build the recap message: LLM synthesis when a summarizer is provided, with a
 * mechanical lane summary as the degradation path so delivery never blocks on an
 * LLM key.
 */
export async function buildRecap(
  feed: RecapFeed,
  summarize: ((prompt: string) => Promise<string>) | null,
): Promise<RecapResult> {
  if (summarize) {
    try {
      const text = await summarize(synthesisPrompt(feed));
      if (text.trim()) return { text: text.trim(), synthesized: true };
    } catch {
      // fall through to mechanical
    }
  }
  return { text: mechanicalRecap(feed), synthesized: false };
}

export function mechanicalRecap(feed: RecapFeed): string {
  const out: string[] = [`Daily Knowledge Base Recap — ${feed.generated}`];
  for (const [group, heading] of [
    ["accounts", "Accounts"],
    ["topics", "Topics"],
  ] as const) {
    const lanes = Object.values(feed[group]);
    if (lanes.length === 0) continue;
    out.push("", `*${heading}*`);
    for (const lane of lanes) {
      out.push(`- ${lane.label}: ${lane.total_new} new note(s)`);
      for (const n of lane.notes.slice(0, 3)) {
        out.push(`  - (${n.date}) ${firstLine(n.text)}`);
      }
    }
  }
  return out.join("\n");
}

function firstLine(text: string): string {
  const line = text.split("\n").find((l) => l.trim()) ?? "";
  return line.length > 160 ? `${line.slice(0, 157)}…` : line;
}
