// RepoClient — the only module that talks to GitHub.
//
// Everything the web app knows about the user's instance comes through here: file
// reads (config, recap feed), file writes (config commits), workflow run status, and
// Actions secrets. One deep module behind a small interface; everything else takes it
// as a dependency. fetch is injectable for tests.

import type { RecapFeed } from "./feed";
import { defaultModelSettings, parseModelSettings, type ModelSettings } from "./modelConfig";

export interface WorkflowRun {
  name: string;
  status: string; // queued | in_progress | completed
  conclusion: string | null; // success | failure | ...
  html_url: string;
  created_at: string;
  path: string; // .github/workflows/<file>.yml
}

export interface RepoFile {
  content: string;
  sha: string;
}

export class RepoClientError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
  }
}

export interface RepoClientOptions {
  repo: string; // "owner/name"
  token: string; // PAT or GitHub App token with contents:rw, actions:read, secrets:rw
  branch?: string;
  fetchFn?: typeof fetch;
}

const API = "https://api.github.com";

export class RepoClient {
  private repo: string;
  private token: string;
  private branch: string;
  private fetchFn: typeof fetch;

  constructor(opts: RepoClientOptions) {
    this.repo = opts.repo;
    this.token = opts.token;
    this.branch = opts.branch ?? "main";
    this.fetchFn = opts.fetchFn ?? fetch;
  }

  private async api(path: string, init?: RequestInit): Promise<Response> {
    const res = await this.fetchFn(`${API}/repos/${this.repo}${path}`, {
      ...init,
      headers: {
        Authorization: `Bearer ${this.token}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
    });
    if (!res.ok) {
      throw new RepoClientError(
        `GitHub API ${init?.method ?? "GET"} ${path} -> ${res.status}`,
        res.status,
      );
    }
    return res;
  }

  /** Read a file from the configured branch. Throws RepoClientError(404) if absent. */
  async getFile(path: string): Promise<RepoFile> {
    const res = await this.api(
      `/contents/${encodePath(path)}?ref=${encodeURIComponent(this.branch)}`,
    );
    const body = (await res.json()) as { content: string; sha: string };
    return {
      content: Buffer.from(body.content, "base64").toString("utf-8"),
      sha: body.sha,
    };
  }

  /**
   * Create or update a file as a commit on the configured branch.
   * Pass the sha from getFile when updating — GitHub rejects a stale sha with 409/422,
   * which callers surface as an edit conflict instead of silently overwriting.
   */
  async putFile(
    path: string,
    content: string,
    message: string,
    sha?: string,
  ): Promise<{ sha: string }> {
    const res = await this.api(`/contents/${encodePath(path)}`, {
      method: "PUT",
      body: JSON.stringify({
        message,
        content: Buffer.from(content, "utf-8").toString("base64"),
        branch: this.branch,
        ...(sha ? { sha } : {}),
      }),
    });
    const body = (await res.json()) as { content: { sha: string } };
    return { sha: body.content.sha };
  }

  /** The recap feed from the default branch, or null when it doesn't exist yet. */
  async getRecapFeed(): Promise<RecapFeed | null> {
    try {
      const file = await this.getFile("compile/recap-feed.json");
      return JSON.parse(file.content) as RecapFeed;
    } catch (e) {
      if (e instanceof RepoClientError && e.status === 404) return null;
      throw e;
    }
  }

  /** Model provider settings from config/models.toml, or defaults when absent. */
  async getModelSettings(): Promise<ModelSettings> {
    try {
      const file = await this.getFile("config/models.toml");
      return parseModelSettings(file.content);
    } catch (e) {
      if (e instanceof RepoClientError && e.status === 404) return defaultModelSettings();
      throw e;
    }
  }

  /** Most recent workflow runs (all workflows, newest first). */
  async listWorkflowRuns(perPage = 30): Promise<WorkflowRun[]> {
    const res = await this.api(`/actions/runs?per_page=${perPage}`);
    const body = (await res.json()) as { workflow_runs: WorkflowRun[] };
    return body.workflow_runs.map((r) => ({
      name: r.name,
      status: r.status,
      conclusion: r.conclusion,
      html_url: r.html_url,
      created_at: r.created_at,
      path: r.path,
    }));
  }

  /** Repo public key for sealing Actions secrets (used by the secrets module). */
  async getSecretsPublicKey(): Promise<{ key_id: string; key: string }> {
    const res = await this.api("/actions/secrets/public-key");
    return (await res.json()) as { key_id: string; key: string };
  }

  /** Store an already-sealed secret value (sealing lives in lib/secrets, not here). */
  async putSealedSecret(
    name: string,
    encryptedValue: string,
    keyId: string,
  ): Promise<void> {
    await this.api(`/actions/secrets/${encodeURIComponent(name)}`, {
      method: "PUT",
      body: JSON.stringify({ encrypted_value: encryptedValue, key_id: keyId }),
    });
  }

  /** Actions secret names for setup status checks. Values are never readable. */
  async listActionSecretNames(): Promise<string[]> {
    const res = await this.api("/actions/secrets?per_page=100");
    const body = (await res.json()) as { secrets?: Array<{ name: string }> };
    return (body.secrets ?? []).map((secret) => secret.name);
  }
}

function encodePath(path: string): string {
  return path.split("/").map(encodeURIComponent).join("/");
}

/** Build the client from the deploy's env vars; throws a setup-friendly error if unset. */
export function repoClientFromEnv(env = process.env): RepoClient {
  const repo = env.GITHUB_REPO;
  const token = env.GITHUB_TOKEN;
  if (!repo || !token) {
    throw new Error(
      "GITHUB_REPO and GITHUB_TOKEN must be set (see web/README.md for deploy setup).",
    );
  }
  return new RepoClient({ repo, token, branch: env.GITHUB_BRANCH ?? "main" });
}
