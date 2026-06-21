"use client";

import { useEffect, useMemo, useState } from "react";
import type { AccountEntry, TopicEntry } from "@/lib/configModel";
import { currentAssignments } from "@/lib/folderAssign";
import {
  buildHomepageConfigPayload,
  countMappedFolders,
  hasAnySource,
  hasBookmarkMapping,
  mergeStarterAccounts,
  missingStarterAccounts,
  STARTER_ACCOUNTS,
  type AuthEnvStatus,
  type DemoFeedPreview,
  type HomeSetupState,
  type SetupCheck,
  type SetupTone,
} from "@/lib/home";
import { MODEL_PROVIDERS, type ModelSettings } from "@/lib/modelConfig";

interface Folder {
  id: string;
  name: string;
}

export type HomeRepoState =
  | {
      kind: "ready";
      topics: TopicEntry[];
      accounts: AccountEntry[];
      models: ModelSettings;
      topicsSha: string | null;
      accountsSha: string | null;
      modelsSha: string | null;
      feedGenerated: string | null;
      feedTotalNew: number | null;
      demoFeed: DemoFeedPreview | null;
      healthOk: boolean | null;
    }
  | { kind: "error"; message: string };

type FolderStatus =
  | { kind: "idle" }
  | { kind: "loading" }
  | { kind: "ready" }
  | { kind: "error"; message: string };

type SaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; messages: string[] };

type SlackStatus =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "configured"; message: string }
  | { kind: "saving" }
  | { kind: "sent"; message: string }
  | { kind: "error"; message: string };

interface HomeDashboardProps {
  sessionUsername: string | null;
  auth: AuthEnvStatus;
  setup: HomeSetupState;
  repo: HomeRepoState;
  demoFeed: DemoFeedPreview | null;
}

export default function HomeDashboard({
  sessionUsername,
  auth,
  setup,
  repo,
  demoFeed,
}: HomeDashboardProps) {
  const repoReady = repo.kind === "ready";
  const [topics, setTopics] = useState<TopicEntry[]>(repoReady ? repo.topics : []);
  const [accounts, setAccounts] = useState<AccountEntry[]>(repoReady ? repo.accounts : []);
  const [models, setModels] = useState<ModelSettings>(
    repoReady ? repo.models : { provider: "openai", model: "", compileModel: "", recapModel: "" },
  );
  const [shas, setShas] = useState<{
    topicsSha: string | null;
    accountsSha: string | null;
    modelsSha: string | null;
  }>({
    topicsSha: repoReady ? repo.topicsSha : null,
    accountsSha: repoReady ? repo.accountsSha : null,
    modelsSha: repoReady ? repo.modelsSha : null,
  });
  const [folders, setFolders] = useState<Folder[]>([]);
  const [assignments, setAssignments] = useState<Record<string, string>>({});
  const [folderStatus, setFolderStatus] = useState<FolderStatus>({ kind: "idle" });
  const [saveStatus, setSaveStatus] = useState<SaveStatus>({ kind: "idle" });
  const [slackWebhookUrl, setSlackWebhookUrl] = useState("");
  const [slackStatus, setSlackStatus] = useState<SlackStatus>({ kind: "idle" });
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    if (!sessionUsername || !repoReady) {
      setFolderStatus({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setFolderStatus({ kind: "loading" });
    fetch("/api/folders")
      .then(async (res) => {
        if (!res.ok) throw new Error((await res.json()).error ?? `HTTP ${res.status}`);
        return res.json();
      })
      .then((data: { folders: Folder[] }) => {
        if (cancelled) return;
        const visibleFolders = data.folders ?? [];
        setFolders(visibleFolders);
        const current = currentAssignments(
          repo.topics,
          visibleFolders.map((folder) => folder.id),
        );
        setAssignments(Object.fromEntries(current.entries()));
        setFolderStatus({ kind: "ready" });
      })
      .catch((error) => {
        if (!cancelled) {
          setFolderStatus({ kind: "error", message: String(error.message ?? error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [repo, repoReady, sessionUsername]);

  useEffect(() => {
    if (!sessionUsername || !repoReady) {
      setSlackStatus({ kind: "idle" });
      return;
    }
    let cancelled = false;
    setSlackStatus({ kind: "checking" });
    fetch("/api/slack")
      .then(async (res) => {
        if (!res.ok) throw new Error((await res.json()).error ?? `HTTP ${res.status}`);
        return res.json();
      })
      .then((data: { configured: boolean; localConfigured: boolean }) => {
        if (cancelled) return;
        setSlackStatus(
          data.configured || data.localConfigured
            ? { kind: "configured", message: "Slack delivery is connected." }
            : { kind: "idle" },
        );
      })
      .catch((error) => {
        if (!cancelled) {
          setSlackStatus({ kind: "error", message: String(error.message ?? error) });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [repoReady, sessionUsername]);

  const missingStarter = useMemo(() => missingStarterAccounts(accounts), [accounts]);
  const knownTopics = useMemo(
    () =>
      [
        ...new Set(
          [
            ...topics.map((topic) => topic.name),
            ...accounts.map((account) => account.topic),
            ...STARTER_ACCOUNTS.map((account) => account.topic),
          ].filter(Boolean),
        ),
      ].sort(),
    [accounts, topics],
  );
  const visibleMappedCount = Object.values(assignments).filter(Boolean).length;
  const localMappedCount = folders.length > 0 ? visibleMappedCount : countMappedFolders(topics);
  const localSourceConfigured = accounts.length > 0 || localMappedCount > 0;
  const locallyUsable = Boolean(sessionUsername && repoReady && localSourceConfigured);

  function setDirtyStatus() {
    setDirty(true);
    if (saveStatus.kind === "saved") setSaveStatus({ kind: "idle" });
  }

  function updateAccount(index: number, value: AccountEntry) {
    setAccounts((current) => current.map((account, i) => (i === index ? value : account)));
    setDirtyStatus();
  }

  function removeAccount(index: number) {
    setAccounts((current) => current.filter((_, i) => i !== index));
    setDirtyStatus();
  }

  function addAccount() {
    setAccounts((current) => [...current, { handle: "", topic: "", offTopic: "skip" }]);
    setDirtyStatus();
  }

  function addStarterPack() {
    setAccounts((current) => mergeStarterAccounts(current));
    setDirtyStatus();
  }

  function updateModels(value: ModelSettings) {
    setModels(value);
    setDirtyStatus();
  }

  function updateAssignment(folderId: string, topic: string) {
    setAssignments((current) => ({ ...current, [folderId]: topic }));
    setDirtyStatus();
  }

  async function saveChanges() {
    if (!repoReady) return;
    setSaveStatus({ kind: "saving" });
    const payload = buildHomepageConfigPayload({
      topics,
      accounts,
      folderAssignments: Object.entries(assignments).map(([folderId, topic]) => ({
        folderId,
        topic,
      })),
    });
    const res = await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...payload, models, ...shas }),
    });
    if (res.ok) {
      const out = (await res.json()) as {
        topicsSha: string | null;
        accountsSha: string | null;
        modelsSha: string | null;
      };
      setTopics(payload.topics);
      setAccounts(payload.accounts);
      setShas(out);
      if (folders.length > 0) {
        const current = currentAssignments(
          payload.topics,
          folders.map((folder) => folder.id),
        );
        setAssignments(Object.fromEntries(current.entries()));
      }
      setDirty(false);
      setSaveStatus({ kind: "saved" });
      return;
    }
    const body = await res.json().catch(() => ({}));
    setSaveStatus({
      kind: "error",
      messages: body.problems ?? [body.error ?? `save failed (HTTP ${res.status})`],
    });
  }

  async function saveSlack() {
    const webhookUrl = slackWebhookUrl.trim();
    if (!webhookUrl) {
      setSlackStatus({ kind: "error", message: "Paste a Slack webhook URL first." });
      return;
    }
    setSlackStatus({ kind: "saving" });
    const res = await fetch("/api/slack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ webhookUrl }),
    });
    const body = await res.json().catch(() => ({}));
    if (!res.ok) {
      setSlackStatus({ kind: "error", message: body.error ?? `Slack setup failed (${res.status})` });
      return;
    }
    setSlackWebhookUrl("");
    setSlackStatus({
      kind: "sent",
      message:
        body.postKind === "recap"
          ? "Slack connected and the current recap was posted."
          : "Slack connected and a test message was posted.",
    });
  }

  if (!sessionUsername) {
    return <ConnectionLanding auth={auth} setup={setup} repo={repo} demoFeed={demoFeed} />;
  }

  return (
    <div className="home-shell">
      <section className="home-hero dashboard-hero">
        <div>
          <p className="eyebrow">Bowerbird control center</p>
          <h1>{locallyUsable ? "Setup complete" : "Finish setup"}</h1>
          <p className="hero-copy">
            {locallyUsable ? (
              <>
                Setup complete! You can now look at an example of four monitored X
                accounts and look at their <a href="/recap">recap</a>. We also have
                access to your bookmark folders; choose which ones you want monitored
                and ingested into your wiki. Once selected, the first import reads the
                latest three pieces of content from each selected folder by default,
                then keeps ingesting new items going forward. Ask your setup agent to
                estimate and import all if you want full folder history. Budget up to
                $0.005 per post read for X calls.
              </>
            ) : (
              <>
                Connected as <strong>@{sessionUsername}</strong>. Manage the accounts
                and bookmark folders that feed your knowledge base.
              </>
            )}
          </p>
        </div>
        <div className="hero-actions">
          <a className="button secondary" href="/recap">
            View recap
          </a>
          <a className="button secondary" href="/health">
            Health
          </a>
        </div>
      </section>

      <StatusStrip
        connectedUsername={sessionUsername}
        repo={repo}
        accountsCount={accounts.length}
        mappedCount={localMappedCount}
        feedFreshness={setup.feedFreshness}
      />

      <section className="setup-grid" aria-label="Setup checklist">
        {setup.checks.map((check) => (
          <SetupCard
            key={check.key}
            check={localizeCheck(check, {
              accountsCount: accounts.length,
              mappedCount: localMappedCount,
              sourceConfigured: localSourceConfigured,
            })}
          />
        ))}
      </section>

      {repo.kind === "error" ? (
        <section className="dash-section">
          <div className="section-head">
            <div>
              <p className="eyebrow">Repository</p>
              <h2>GitHub is not reachable</h2>
            </div>
          </div>
          <p className="empty-state">{repo.message}</p>
        </section>
      ) : (
        <>
          <section className="dash-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">Accounts</p>
                <h2>Monitored accounts</h2>
              </div>
              <div className="section-actions">
                {missingStarter.length > 0 && (
                  <button
                    type="button"
                    className={accounts.length === 0 ? "button primary" : "button secondary"}
                    onClick={addStarterPack}
                  >
                    {accounts.length === 0 ? "Add AI starter pack" : "Add missing starters"}
                  </button>
                )}
                <button type="button" className="button secondary" onClick={addAccount}>
                  Add account
                </button>
              </div>
            </div>

            {accounts.length === 0 ? (
              <p className="empty-state">
                No monitored accounts yet. Add the AI starter pack or create your own
                account row.
              </p>
            ) : (
              <div className="manage-list">
                {accounts.map((account, index) => (
                  <div className="manage-row account-row" key={`${account.handle}-${index}`}>
                    <label>
                      <span>Handle</span>
                      <input
                        aria-label={`handle ${index + 1}`}
                        placeholder="@handle"
                        value={account.handle}
                        onChange={(event) =>
                          updateAccount(index, { ...account, handle: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      <span>Topic</span>
                      <input
                        aria-label={`topic for account ${index + 1}`}
                        list="home-topic-names"
                        placeholder="topic-slug"
                        value={account.topic}
                        onChange={(event) =>
                          updateAccount(index, { ...account, topic: event.target.value })
                        }
                      />
                    </label>
                    <label>
                      <span>Label</span>
                      <input
                        aria-label={`label for account ${index + 1}`}
                        placeholder="optional recap label"
                        value={account.label ?? ""}
                        onChange={(event) =>
                          updateAccount(index, { ...account, label: event.target.value })
                        }
                      />
                    </label>
                    <button type="button" className="text-button" onClick={() => removeAccount(index)}>
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="dash-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">Bookmarks</p>
                <h2>Bookmark mapping</h2>
              </div>
              <a className="text-link" href="/folders">
                Advanced folder page
              </a>
            </div>

            {folderStatus.kind === "loading" && <p className="empty-state">Loading X folders...</p>}
            {folderStatus.kind === "error" && (
              <p className="empty-state error-text">
                Could not load bookmark folders: {folderStatus.message}
              </p>
            )}
            {folderStatus.kind === "ready" && folders.length === 0 && (
              <p className="empty-state">No X bookmark folders found. Create folders in X first.</p>
            )}
            {folderStatus.kind === "idle" && (
              <p className="empty-state">Connect X to browse bookmark folders.</p>
            )}
            {folders.length > 0 && (
              <div className="manage-list">
                {folders.map((folder) => (
                  <div className="manage-row folder-row" key={folder.id}>
                    <div>
                      <strong>{folder.name}</strong>
                      <span>{folder.id}</span>
                    </div>
                    <label>
                      <span>Topic</span>
                      <input
                        aria-label={`topic for ${folder.name}`}
                        list="home-topic-names"
                        placeholder="empty = not ingested"
                        value={assignments[folder.id] ?? ""}
                        onChange={(event) => updateAssignment(folder.id, event.target.value)}
                      />
                    </label>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="dash-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">Models</p>
                <h2>Compile and recap provider</h2>
              </div>
            </div>
            <div className="manage-list">
              <div className="manage-row model-row">
                <label>
                  <span>Provider</span>
                  <select
                    aria-label="model provider"
                    value={models.provider}
                    onChange={(event) => {
                      const provider = event.target.value as ModelSettings["provider"];
                      updateModels({
                        provider,
                        model: "",
                        compileModel: "",
                        recapModel: "",
                      });
                    }}
                  >
                    {Object.values(MODEL_PROVIDERS).map((provider) => (
                      <option key={provider.key} value={provider.key}>
                        {provider.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <span>Model override</span>
                  <input
                    aria-label="model override"
                    placeholder="provider default"
                    value={models.model}
                    onChange={(event) =>
                      updateModels({
                        ...models,
                        model: event.target.value,
                        compileModel: "",
                        recapModel: "",
                      })
                    }
                  />
                </label>
                <div className="model-secret">
                  <span>Secret</span>
                  <strong>{MODEL_PROVIDERS[models.provider].apiKeyName}</strong>
                </div>
              </div>
            </div>
          </section>

          <section className="dash-section">
            <div className="section-head">
              <div>
                <p className="eyebrow">Consumers</p>
                <h2>Slack recap</h2>
              </div>
              <a
                className="text-link"
                href="https://api.slack.com/apps?new_app=1"
                target="_blank"
                rel="noreferrer"
              >
                Create Slack app
              </a>
            </div>
            <div className="manage-list">
              <div className="manage-row slack-row">
                <label>
                  <span>Webhook URL</span>
                  <input
                    aria-label="Slack webhook URL"
                    type="password"
                    placeholder="https://hooks.slack.com/services/..."
                    value={slackWebhookUrl}
                    onChange={(event) => setSlackWebhookUrl(event.target.value)}
                  />
                </label>
                <button
                  type="button"
                  className="button secondary"
                  disabled={slackStatus.kind === "saving" || !repoReady}
                  onClick={saveSlack}
                >
                  {slackStatus.kind === "saving" ? "Sending..." : "Save and send test recap"}
                </button>
                <ConnectorStatus status={slackStatus} />
              </div>
            </div>
          </section>

          <datalist id="home-topic-names">
            {knownTopics.map((topic) => (
              <option key={topic} value={topic} />
            ))}
          </datalist>

          <div className="save-dock" aria-live="polite">
            <div>
              <strong>{dirty ? "Unsaved changes" : "Configuration clean"}</strong>
              <span>
                {hasAnySource(accounts, topics) || localSourceConfigured
                  ? "Accounts and bookmark mappings save as one repo commit."
                  : "Add at least one account or mapped folder to make Bowerbird useful."}
              </span>
            </div>
            <button
              type="button"
              className="button primary"
              disabled={saveStatus.kind === "saving" || !repoReady || !dirty}
              onClick={saveChanges}
            >
              {saveStatus.kind === "saving" ? "Saving..." : "Save changes"}
            </button>
            {saveStatus.kind === "saved" && <span className="status-pill complete">Saved</span>}
            {saveStatus.kind === "error" && (
              <ul className="inline-errors">
                {saveStatus.messages.map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function ConnectorStatus({ status }: { status: SlackStatus }) {
  if (status.kind === "checking") {
    return <span className="status-pill info">Checking</span>;
  }
  if (status.kind === "configured" || status.kind === "sent") {
    return (
      <div className="connector-status" aria-live="polite">
        <span className="status-pill complete">Connected</span>
        <small>{status.message}</small>
      </div>
    );
  }
  if (status.kind === "error") {
    return (
      <div className="connector-status" aria-live="polite">
        <span className="status-pill blocked">Error</span>
        <small>{status.message}</small>
      </div>
    );
  }
  return <span className="status-pill pending">Not connected</span>;
}

function ConnectionLanding({
  auth,
  setup,
  repo,
  demoFeed,
}: {
  auth: AuthEnvStatus;
  setup: HomeSetupState;
  repo: HomeRepoState;
  demoFeed: DemoFeedPreview | null;
}) {
  return (
    <div className="home-shell">
      <section className="home-hero">
        <div>
          <p className="eyebrow">Bowerbird setup</p>
          <h1>See the demo. Connect X to make it yours.</h1>
          <p className="hero-copy">
            This repo includes live sample output from four AI accounts. Connect
            your X account to turn this fork from a demo snapshot into your own
            running knowledge base.
          </p>
        </div>
        <div className="connect-panel">
          {auth.ok ? (
            <a className="button primary xl" href="/api/auth/login">
              Connect X
            </a>
          ) : (
            <span className="button primary xl disabled" aria-disabled="true">
              Connect X
            </span>
          )}
          {!auth.ok && (
            <p>
              Missing <code>{auth.missing.join(", ")}</code>. Add these env vars to
              enable OAuth.
            </p>
          )}
        </div>
      </section>

      {demoFeed && <DemoFeedCard preview={demoFeed} />}

      <section className="readiness-list" aria-label="Setup readiness">
        <ReadinessRow
          label="X app"
          ok={auth.ok}
          detail={auth.ok ? "OAuth settings are present." : `Missing ${auth.missing.join(", ")}.`}
        />
        <ReadinessRow
          label="GitHub repo"
          ok={setup.repoReady}
          detail={repo.kind === "ready" ? "Repo is reachable." : repo.message}
        />
        <ReadinessRow label="X session" ok={setup.connected} detail="Not connected yet." />
        <ReadinessRow
          label="Sources"
          ok={setup.sourceConfigured}
          detail={
            setup.sourceConfigured
              ? "At least one source is configured."
              : "No monitored accounts or mapped bookmark folders yet."
          }
        />
      </section>
    </div>
  );
}

function DemoFeedCard({ preview }: { preview: DemoFeedPreview }) {
  return (
    <section className="demo-feed" aria-label="Sample output">
      <div className="section-head">
        <div>
          <p className="eyebrow">Sample output</p>
          <h2>Latest demo recap</h2>
        </div>
        <a className="text-link" href="/recap">
          Open recap
        </a>
      </div>
      <p className="demo-copy">
        The public Bowerbird repo keeps a living sample wiki from the four starter
        AI accounts. Your fork starts with that snapshot; after setup, future
        recaps come from the sources you keep or add.
      </p>
      <div className="demo-summary">
        <span>Generated {preview.generated}</span>
        <span>{preview.totalNew} new note{preview.totalNew === 1 ? "" : "s"}</span>
        <span>{preview.accountLanes} account lane{preview.accountLanes === 1 ? "" : "s"}</span>
      </div>
      {preview.lanes.length > 0 && (
        <div className="demo-lanes">
          {preview.lanes.map((lane) => (
            <article key={`${lane.key}-${lane.label}`} className="demo-lane">
              <strong>{lane.label}</strong>
              <span>{lane.totalNew} new</span>
              {lane.notes.map((note) => (
                <p key={note}>{note}</p>
              ))}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function StatusStrip({
  connectedUsername,
  repo,
  accountsCount,
  mappedCount,
  feedFreshness,
}: {
  connectedUsername: string;
  repo: HomeRepoState;
  accountsCount: number;
  mappedCount: number;
  feedFreshness: string;
}) {
  return (
    <section className="status-grid" aria-label="Current status">
      <StatusCard label="X connection" value={`@${connectedUsername}`} tone="complete" />
      <StatusCard
        label="Repository"
        value={repo.kind === "ready" ? "Reachable" : "Needs setup"}
        tone={repo.kind === "ready" ? "complete" : "blocked"}
      />
      <StatusCard
        label="Sources"
        value={`${accountsCount} accounts / ${mappedCount} folders`}
        tone={accountsCount > 0 || mappedCount > 0 ? "complete" : "pending"}
      />
      <StatusCard
        label="Recap"
        value={feedFreshness}
        tone={feedFreshness === "fresh" ? "complete" : "info"}
      />
    </section>
  );
}

function StatusCard({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: SetupTone;
}) {
  return (
    <div className="status-card">
      <span>{label}</span>
      <strong>{value}</strong>
      <i className={`status-dot ${tone}`} aria-hidden="true" />
    </div>
  );
}

function SetupCard({ check }: { check: SetupCheck }) {
  return (
    <article className="setup-card">
      <span className={`status-pill ${check.tone}`}>{labelForTone(check.tone)}</span>
      <h3>{check.label}</h3>
      <p>{check.detail}</p>
    </article>
  );
}

function ReadinessRow({
  label,
  ok,
  detail,
}: {
  label: string;
  ok: boolean;
  detail: string;
}) {
  return (
    <div className="readiness-row">
      <div>
        <strong>{label}</strong>
        <span>{detail}</span>
      </div>
      <span className={`status-pill ${ok ? "complete" : "blocked"}`}>
        {ok ? "Ready" : "Missing"}
      </span>
    </div>
  );
}

function localizeCheck(
  check: SetupCheck,
  local: { accountsCount: number; mappedCount: number; sourceConfigured: boolean },
): SetupCheck {
  if (check.key === "accounts") {
    return {
      ...check,
      tone: local.accountsCount > 0 ? "complete" : "pending",
      detail:
        local.accountsCount > 0
          ? `${local.accountsCount} account${local.accountsCount === 1 ? "" : "s"} staged.`
          : "Add accounts to mirror posts and replies.",
    };
  }
  if (check.key === "bookmarks") {
    return {
      ...check,
      tone: local.mappedCount > 0 ? "complete" : "pending",
      detail:
        local.mappedCount > 0
          ? `${local.mappedCount} folder${local.mappedCount === 1 ? "" : "s"} mapped or staged.`
          : "Assign at least one X bookmark folder to a topic.",
    };
  }
  return check;
}

function labelForTone(tone: SetupTone): string {
  if (tone === "complete") return "Done";
  if (tone === "blocked") return "Blocked";
  if (tone === "info") return "Info";
  return "Next";
}
