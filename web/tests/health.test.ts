// Health derivation: feed freshness states, per-workflow latest-run mapping, the
// ok/needs-attention rollup.
import { describe, expect, it } from "vitest";
import { deriveHealth } from "@/lib/health";
import type { WorkflowRun } from "@/lib/repoClient";

const TODAY = "2026-06-12";

function feed(generated: string, totalNew = 3) {
  return {
    generated,
    window_hours: 24,
    accounts: {},
    topics: {},
    summary: { total_new: totalNew, account_lanes: 0, topic_lanes: 1 },
  };
}

function run(file: string, conclusion: string | null, status = "completed", at = "2026-06-12T01:00:00Z"): WorkflowRun {
  return {
    name: file,
    status,
    conclusion,
    html_url: `https://github.com/x/${file}`,
    created_at: at,
    path: `.github/workflows/${file}`,
  };
}

describe("deriveHealth", () => {
  it("healthy: fresh feed, all workflows green", () => {
    const h = deriveHealth(
      feed(TODAY),
      [
        run("pull.yml", "success"),
        run("account-dump.yml", "success"),
        run("compile.yml", "success"),
        run("kb-recap-feed.yml", "success"),
        run("slack-recap.yml", "success"),
      ],
      TODAY,
    );
    expect(h.ok).toBe(true);
    expect(h.feed).toBe("fresh");
    expect(h.workflows.map((w) => w.status)).toEqual([
      "success",
      "success",
      "success",
      "success",
      "success",
    ]);
  });

  it("stale feed needs attention even when runs are green", () => {
    const h = deriveHealth(feed("2026-06-09"), [run("pull.yml", "success")], TODAY);
    expect(h.feed).toBe("stale");
    expect(h.ok).toBe(false);
  });

  it("a failing workflow flips the rollup", () => {
    const h = deriveHealth(feed(TODAY), [run("pull.yml", "failure"), run("compile.yml", "success")], TODAY);
    expect(h.workflows.find((w) => w.key === "pull")?.status).toBe("failure");
    expect(h.ok).toBe(false);
  });

  it("uses the LATEST run per workflow (list is newest-first)", () => {
    const h = deriveHealth(
      feed(TODAY),
      [run("pull.yml", "success", "completed", "2026-06-12T02:00:00Z"), run("pull.yml", "failure", "completed", "2026-06-11T02:00:00Z")],
      TODAY,
    );
    expect(h.workflows.find((w) => w.key === "pull")?.status).toBe("success");
  });

  it("in-progress runs show as running, not failing", () => {
    const h = deriveHealth(feed(TODAY), [run("compile.yml", null, "in_progress")], TODAY);
    expect(h.workflows.find((w) => w.key === "compile")?.status).toBe("running");
  });

  it("missing feed and never-ran workflows on a fresh fork", () => {
    const h = deriveHealth(null, [], TODAY);
    expect(h.feed).toBe("missing");
    expect(h.ok).toBe(false);
    expect(h.workflows.every((w) => w.status === "never-ran")).toBe(true);
  });
});
