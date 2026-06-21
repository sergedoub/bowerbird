import { mkdtemp, mkdir, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { localRecapFeedPaths, readLocalRecapFeed } from "@/lib/localFeed";

function demoFeed() {
  return {
    generated: "2026-06-20",
    window_hours: 24,
    accounts: {},
    topics: {
      "getting-started": {
        label: "Getting started",
        total_new: 1,
        notes: [
          {
            date: "2026-06-20",
            file: "wiki/getting-started/sources/demo.md",
            text: "Bowerbird has demo output.",
          },
        ],
      },
    },
    summary: { total_new: 1, account_lanes: 0, topic_lanes: 1 },
  };
}

describe("local recap feed", () => {
  it("checks repo-root and web-root launch paths", () => {
    const repoRoot = "/tmp/bowerbird";
    expect(localRecapFeedPaths(repoRoot)).toEqual([
      "/tmp/bowerbird/compile/recap-feed.json",
      "/tmp/compile/recap-feed.json",
    ]);
    expect(localRecapFeedPaths(path.join(repoRoot, "web"))).toEqual([
      "/tmp/bowerbird/web/compile/recap-feed.json",
      "/tmp/bowerbird/compile/recap-feed.json",
    ]);
  });

  it("reads the local demo feed when launched from web/", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "bowerbird-feed-"));
    await mkdir(path.join(root, "compile"));
    await mkdir(path.join(root, "web"));
    await writeFile(
      path.join(root, "compile", "recap-feed.json"),
      JSON.stringify(demoFeed()),
    );

    await expect(readLocalRecapFeed(path.join(root, "web"))).resolves.toEqual(demoFeed());
  });

  it("returns null when the local feed is missing or invalid", async () => {
    const root = await mkdtemp(path.join(tmpdir(), "bowerbird-feed-"));
    await mkdir(path.join(root, "compile"));
    await writeFile(path.join(root, "compile", "recap-feed.json"), "{\"generated\":true}");

    await expect(readLocalRecapFeed(root)).resolves.toBeNull();
    await expect(readLocalRecapFeed(path.join(root, "missing"))).resolves.toBeNull();
  });
});
