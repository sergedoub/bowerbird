// Folder->topic assignment: preserves invisible ids, moves visible ones, drops
// emptied topics, single-owner by construction.
import { describe, expect, it } from "vitest";
import { applyAssignments, currentAssignments } from "@/lib/folderAssign";

const existing = [
  { name: "marketing", folderIds: ["111", "999"] }, // 999 not visible in the browser
  { name: "ai", folderIds: ["222"] },
];

describe("applyAssignments", () => {
  it("moves a visible folder between topics and keeps invisible ids", () => {
    const out = applyAssignments(existing, [
      { folderId: "111", topic: "ai" },
      { folderId: "222", topic: "ai" },
    ]);
    expect(out).toEqual([
      { name: "marketing", folderIds: ["999"] },
      { name: "ai", folderIds: ["111", "222"] },
    ]);
  });

  it("creates new topics and drops topics that end up empty", () => {
    const out = applyAssignments([{ name: "ai", folderIds: ["222"] }], [
      { folderId: "222", topic: "new-topic" },
    ]);
    expect(out).toEqual([{ name: "new-topic", folderIds: ["222"] }]);
  });

  it("unassigning (empty topic) removes a visible folder from the config", () => {
    const out = applyAssignments(existing, [
      { folderId: "111", topic: "" },
      { folderId: "222", topic: "ai" },
    ]);
    expect(out).toEqual([
      { name: "marketing", folderIds: ["999"] },
      { name: "ai", folderIds: ["222"] },
    ]);
  });

  it("a folder can only land in one topic (last write wins per map semantics)", () => {
    const out = applyAssignments([], [{ folderId: "1", topic: "a" }]);
    expect(out.flatMap((t) => t.folderIds).filter((id) => id === "1")).toHaveLength(1);
  });
});

describe("currentAssignments", () => {
  it("derives each visible folder's owning topic, empty when unowned", () => {
    const map = currentAssignments(existing, ["111", "222", "333"]);
    expect(map.get("111")).toBe("marketing");
    expect(map.get("222")).toBe("ai");
    expect(map.get("333")).toBe("");
  });
});
