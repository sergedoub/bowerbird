// Recap engine: the freshness/zero-content guards (the most important operational
// rules), synthesis with an injected LLM, and the mechanical fallback.
import { describe, expect, it } from "vitest";
import type { RecapFeed } from "@/lib/feed";
import {
  buildRecap,
  mechanicalRecap,
  quietMessage,
  shouldDeliver,
  synthesisPrompt,
} from "@/lib/recap";

const TODAY = "2026-06-12";

function feed(overrides: Partial<RecapFeed> = {}): RecapFeed {
  return {
    generated: TODAY,
    window_hours: 24,
    accounts: {
      bcherny: {
        label: "Boris (Anthropic)",
        total_new: 2,
        notes: [
          { date: TODAY, file: "wiki/claude-code/sources/a.md", text: "Tip: use auto mode for refactors." },
          { date: TODAY, file: "wiki/claude-code/sources/b.md", text: "Hooks ship next week." },
        ],
      },
    },
    topics: {
      marketing: {
        label: "Marketing",
        total_new: 1,
        notes: [{ date: TODAY, file: "wiki/marketing/sources/c.md", text: "Pricing pages convert 3x with social proof." }],
      },
    },
    summary: { total_new: 3, account_lanes: 1, topic_lanes: 1 },
    ...overrides,
  };
}

describe("shouldDeliver — the freshness guard", () => {
  it("delivers a fresh feed with content", () => {
    expect(shouldDeliver(feed(), TODAY, { quietMessageOnEmpty: false })).toEqual({
      deliver: true,
      quiet: false,
    });
  });

  it("NEVER delivers a stale feed (old notes must not look new)", () => {
    const d = shouldDeliver(feed({ generated: "2026-06-09" }), TODAY, { quietMessageOnEmpty: true });
    expect(d.deliver).toBe(false);
    if (!d.deliver) expect(d.reason).toContain("stale");
  });

  it("skips when there is no feed yet", () => {
    expect(shouldDeliver(null, TODAY, { quietMessageOnEmpty: true }).deliver).toBe(false);
  });

  it("zero-new days: silent by default, quiet message when opted in", () => {
    const empty = feed({ summary: { total_new: 0, account_lanes: 0, topic_lanes: 0 } });
    expect(shouldDeliver(empty, TODAY, { quietMessageOnEmpty: false }).deliver).toBe(false);
    expect(shouldDeliver(empty, TODAY, { quietMessageOnEmpty: true })).toEqual({
      deliver: true,
      quiet: true,
    });
    expect(quietMessage(empty)).toContain("quiet day");
  });
});

describe("synthesis", () => {
  it("the prompt carries every lane, the labels, and the note bodies", () => {
    const prompt = synthesisPrompt(feed());
    expect(prompt).toContain("Boris (Anthropic)");
    expect(prompt).toContain("Marketing");
    expect(prompt).toContain("auto mode for refactors");
    expect(prompt).toContain("social proof");
    expect(prompt).toContain(`Daily Knowledge Base Recap — ${TODAY}`);
  });

  it("uses the injected LLM and returns its text", async () => {
    const result = await buildRecap(feed(), async (p) => {
      expect(p).toContain("Lanes:");
      return "  synthesized recap  ";
    });
    expect(result).toEqual({ text: "synthesized recap", synthesized: true });
  });

  it("falls back to the mechanical recap when the LLM fails or is absent", async () => {
    const noLlm = await buildRecap(feed(), null);
    expect(noLlm.synthesized).toBe(false);
    expect(noLlm.text).toContain("Boris (Anthropic): 2 new note(s)");

    const failing = await buildRecap(feed(), async () => {
      throw new Error("api down");
    });
    expect(failing.synthesized).toBe(false);
  });

  it("mechanical recap covers every lane and stays compact", () => {
    const text = mechanicalRecap(feed());
    expect(text).toContain("*Accounts*");
    expect(text).toContain("*Topics*");
    expect(text).toContain("Marketing: 1 new note(s)");
  });
});
