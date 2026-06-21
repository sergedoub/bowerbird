// Folder -> topic assignment: turn the browser's per-folder choices into a new
// topics config, preserving folder ids that aren't visible in the browser (e.g.
// folders deleted on X but still configured). Pure; the no-folder-feeds-two-topics
// rule holds by construction since assignments map each folder to at most one topic.

import type { TopicEntry } from "./configModel";

export interface FolderAssignment {
  folderId: string;
  topic: string; // "" = unassigned
}

export function applyAssignments(
  existing: TopicEntry[],
  assignments: FolderAssignment[],
): TopicEntry[] {
  const visible = new Set(assignments.map((a) => a.folderId));

  // Start from existing topics with browser-visible ids removed (they get re-added
  // wherever they're now assigned); invisible ids stay where they were.
  const byTopic = new Map<string, string[]>();
  for (const t of existing) {
    byTopic.set(
      t.name,
      t.folderIds.filter((id) => !visible.has(id)),
    );
  }

  for (const a of assignments) {
    const topic = a.topic.trim();
    if (!topic) continue;
    if (!byTopic.has(topic)) byTopic.set(topic, []);
    byTopic.get(topic)!.push(a.folderId);
  }

  // Preserve existing topic order, append new topics in assignment order; drop
  // topics that ended up empty (nothing references them anymore).
  const order = [...existing.map((t) => t.name)];
  for (const name of byTopic.keys()) {
    if (!order.includes(name)) order.push(name);
  }
  return order
    .map((name) => ({ name, folderIds: byTopic.get(name) ?? [] }))
    .filter((t) => t.folderIds.length > 0);
}

/** The current assignment of each visible folder, derived from the topics config. */
export function currentAssignments(
  topics: TopicEntry[],
  folderIds: string[],
): Map<string, string> {
  const owner = new Map<string, string>();
  for (const t of topics) {
    for (const id of t.folderIds) owner.set(id, t.name);
  }
  return new Map(folderIds.map((id) => [id, owner.get(id) ?? ""]));
}
