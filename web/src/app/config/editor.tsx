"use client";

import { useEffect, useState } from "react";

interface TopicRow {
  name: string;
  folderIdsText: string; // comma/space separated in the form
}

interface AccountRow {
  handle: string;
  topic: string;
  label: string;
  offTopic: "skip" | "quarantine";
}

type Status =
  | { kind: "loading" }
  | { kind: "ready" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; messages: string[] };

export default function ConfigEditor() {
  const [topics, setTopics] = useState<TopicRow[]>([]);
  const [accounts, setAccounts] = useState<AccountRow[]>([]);
  const [shas, setShas] = useState<{ topicsSha: string | null; accountsSha: string | null }>({
    topicsSha: null,
    accountsSha: null,
  });
  const [status, setStatus] = useState<Status>({ kind: "loading" });

  useEffect(() => {
    fetch("/api/config")
      .then(async (res) => {
        if (!res.ok) throw new Error((await res.json()).error ?? `HTTP ${res.status}`);
        return res.json();
      })
      .then((data) => {
        setTopics(
          data.topics.map((t: { name: string; folderIds: string[] }) => ({
            name: t.name,
            folderIdsText: t.folderIds.join(", "),
          })),
        );
        setAccounts(
          data.accounts.map((a: { handle: string; topic: string; label?: string; offTopic: string }) => ({
            handle: a.handle,
            topic: a.topic,
            label: a.label ?? "",
            offTopic: a.offTopic === "quarantine" ? "quarantine" : "skip",
          })),
        );
        setShas({ topicsSha: data.topicsSha, accountsSha: data.accountsSha });
        setStatus({ kind: "ready" });
      })
      .catch((e) => setStatus({ kind: "error", messages: [String(e.message ?? e)] }));
  }, []);

  async function save() {
    setStatus({ kind: "saving" });
    const payload = {
      topics: topics.map((t) => ({
        name: t.name.trim(),
        folderIds: t.folderIdsText
          .split(/[\s,]+/)
          .map((s) => s.trim())
          .filter(Boolean),
      })),
      accounts: accounts.map((a) => ({
        handle: a.handle.trim().replace(/^@/, ""),
        topic: a.topic.trim(),
        offTopic: a.offTopic,
        ...(a.label.trim() ? { label: a.label.trim() } : {}),
      })),
      ...shas,
    };
    const res = await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (res.ok) {
      const out = await res.json();
      setShas(out);
      setStatus({ kind: "saved" });
      return;
    }
    const body = await res.json().catch(() => ({}));
    setStatus({
      kind: "error",
      messages: body.problems ?? [body.error ?? `save failed (HTTP ${res.status})`],
    });
  }

  if (status.kind === "loading") return <p className="meta">Loading config…</p>;

  return (
    <div className="config-editor">
      <h2>Bookmark topics</h2>
      <p className="meta">
        Map X bookmark folders to wiki topics. Find folder ids on the{" "}
        <a href="/folders">folder browser</a> or with <code>bowerbird folders</code>.
      </p>
      {topics.map((t, i) => (
        <div className="row" key={i}>
          <input
            aria-label="topic name"
            placeholder="topic-name"
            value={t.name}
            onChange={(e) => setTopics(update(topics, i, { ...t, name: e.target.value }))}
          />
          <input
            aria-label="folder ids"
            placeholder="folder ids (comma separated)"
            value={t.folderIdsText}
            onChange={(e) =>
              setTopics(update(topics, i, { ...t, folderIdsText: e.target.value }))
            }
            style={{ flex: 2 }}
          />
          <button type="button" onClick={() => setTopics(remove(topics, i))}>
            remove
          </button>
        </div>
      ))}
      <button type="button" onClick={() => setTopics([...topics, { name: "", folderIdsText: "" }])}>
        + add topic
      </button>

      <h2>Mirrored accounts</h2>
      <p className="meta">Full posts + replies, distilled into the bound topic. Each mirrored post is a paid API read.</p>
      {accounts.map((a, i) => (
        <div className="row" key={i}>
          <input
            aria-label="handle"
            placeholder="handle"
            value={a.handle}
            onChange={(e) => setAccounts(update(accounts, i, { ...a, handle: e.target.value }))}
          />
          <input
            aria-label="account topic"
            placeholder="topic"
            value={a.topic}
            onChange={(e) => setAccounts(update(accounts, i, { ...a, topic: e.target.value }))}
          />
          <input
            aria-label="label"
            placeholder="recap label (optional)"
            value={a.label}
            onChange={(e) => setAccounts(update(accounts, i, { ...a, label: e.target.value }))}
          />
          <button type="button" onClick={() => setAccounts(remove(accounts, i))}>
            remove
          </button>
        </div>
      ))}
      <button
        type="button"
        onClick={() =>
          setAccounts([...accounts, { handle: "", topic: "", label: "", offTopic: "skip" }])
        }
      >
        + add account
      </button>

      <div className="save-bar">
        <button type="button" className="primary" disabled={status.kind === "saving"} onClick={save}>
          {status.kind === "saving" ? "Saving…" : "Save (commits to repo)"}
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
    </div>
  );
}

function update<T>(arr: T[], i: number, value: T): T[] {
  return arr.map((x, j) => (j === i ? value : x));
}

function remove<T>(arr: T[], i: number): T[] {
  return arr.filter((_, j) => j !== i);
}
