"use client";

import { useEffect, useState } from "react";
import type { TopicEntry } from "@/lib/configModel";
import { applyAssignments, currentAssignments } from "@/lib/folderAssign";

interface Folder {
  id: string;
  name: string;
}

type Status =
  | { kind: "loading" }
  | { kind: "ready" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; messages: string[] };

export default function FolderBrowser() {
  const [folders, setFolders] = useState<Folder[]>([]);
  const [topics, setTopics] = useState<TopicEntry[]>([]);
  const [accountsPassthrough, setAccountsPassthrough] = useState<unknown[]>([]);
  const [shas, setShas] = useState<{ topicsSha: string | null; accountsSha: string | null }>({
    topicsSha: null,
    accountsSha: null,
  });
  const [assign, setAssign] = useState<Map<string, string>>(new Map());
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    Promise.all([
      fetch("/api/folders").then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).error ?? `HTTP ${r.status}`);
        return r.json();
      }),
      fetch("/api/config").then(async (r) => {
        if (!r.ok) throw new Error((await r.json()).error ?? `HTTP ${r.status}`);
        return r.json();
      }),
    ])
      .then(([f, c]) => {
        setFolders(f.folders);
        setTopics(c.topics);
        setAccountsPassthrough(c.accounts);
        setShas({ topicsSha: c.topicsSha, accountsSha: c.accountsSha });
        setAssign(
          currentAssignments(
            c.topics,
            f.folders.map((x: Folder) => x.id),
          ),
        );
        setStatus({ kind: "ready" });
      })
      .catch((e) => setStatus({ kind: "error", messages: [String(e.message ?? e)] }));
  }, []);

  async function save() {
    setStatus({ kind: "saving" });
    const newTopics = applyAssignments(
      topics,
      [...assign.entries()].map(([folderId, topic]) => ({ folderId, topic })),
    );
    const res = await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ topics: newTopics, accounts: accountsPassthrough, ...shas }),
    });
    if (res.ok) {
      const out = await res.json();
      setShas(out);
      setTopics(newTopics);
      setStatus({ kind: "saved" });
      return;
    }
    const body = await res.json().catch(() => ({}));
    setStatus({
      kind: "error",
      messages: body.problems ?? [body.error ?? `save failed (HTTP ${res.status})`],
    });
  }

  if (status.kind === "loading") return <p className="meta">Loading folders…</p>;
  if (status.kind === "error" && folders.length === 0)
    return (
      <ul className="problems">
        {status.messages.map((m) => (
          <li key={m}>{m}</li>
        ))}
      </ul>
    );

  const knownTopics = [...new Set(topics.map((t) => t.name))];

  return (
    <div className="config-editor">
      {folders.length === 0 && (
        <p className="empty">No bookmark folders found — create folders in the X app first.</p>
      )}
      {folders.map((f) => (
        <div className="row" key={f.id}>
          <span style={{ flex: 1 }}>
            {f.name} <span className="meta">({f.id})</span>
          </span>
          <input
            aria-label={`topic for ${f.name}`}
            placeholder="topic (empty = not ingested)"
            list="topic-names"
            value={assign.get(f.id) ?? ""}
            onChange={(e) => setAssign(new Map(assign).set(f.id, e.target.value))}
          />
        </div>
      ))}
      <datalist id="topic-names">
        {knownTopics.map((t) => (
          <option key={t} value={t} />
        ))}
      </datalist>

      {folders.length > 0 && (
        <div className="save-bar">
          <button type="button" className="primary" disabled={status.kind === "saving"} onClick={save}>
            {status.kind === "saving" ? "Saving…" : "Save mapping (commits to repo)"}
          </button>
          {status.kind === "saved" && <span className="badge fresh">saved</span>}
          {status.kind === "error" && (
            <ul className="problems">
              {status.messages.map((m) => (
                <li key={m}>{m}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
