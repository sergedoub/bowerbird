// RepoClient against a fake fetch: encoding, auth headers, stale-sha conflicts,
// 404-as-null for the feed. No network.
import { describe, expect, it } from "vitest";
import { RepoClient, RepoClientError } from "@/lib/repoClient";

type Handler = (url: string, init?: RequestInit) => Response | undefined;

function fakeFetch(handler: Handler): { fetchFn: typeof fetch; calls: { url: string; init?: RequestInit }[] } {
  const calls: { url: string; init?: RequestInit }[] = [];
  const fetchFn = (async (input: any, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });
    const res = handler(url, init);
    return res ?? new Response("not found", { status: 404 });
  }) as typeof fetch;
  return { fetchFn, calls };
}

function client(handler: Handler) {
  const { fetchFn, calls } = fakeFetch(handler);
  return {
    repo: new RepoClient({ repo: "owner/kb", token: "tok", fetchFn }),
    calls,
  };
}

const b64 = (s: string) => Buffer.from(s, "utf-8").toString("base64");

describe("getFile", () => {
  it("decodes base64 content and returns the sha", async () => {
    const { repo, calls } = client((url) => {
      if (url.includes("/contents/config/topics.toml")) {
        return Response.json({ content: b64("[topics.m]\n"), sha: "abc" });
      }
    });
    const file = await repo.getFile("config/topics.toml");
    expect(file).toEqual({ content: "[topics.m]\n", sha: "abc" });
    expect(calls[0].url).toContain("ref=main");
    expect((calls[0].init?.headers as any).Authorization).toBe("Bearer tok");
  });

  it("throws a typed error carrying the HTTP status", async () => {
    const { repo } = client(() => undefined);
    await expect(repo.getFile("missing.md")).rejects.toMatchObject({ status: 404 });
  });
});

describe("putFile", () => {
  it("sends base64 content with branch and optional sha", async () => {
    const { repo, calls } = client((url, init) => {
      if (init?.method === "PUT") {
        return Response.json({ content: { sha: "new-sha" } });
      }
    });
    const out = await repo.putFile("config/topics.toml", "x = 1\n", "msg", "old-sha");
    expect(out.sha).toBe("new-sha");
    const body = JSON.parse(String(calls[0].init?.body));
    expect(body).toMatchObject({ message: "msg", branch: "main", sha: "old-sha" });
    expect(Buffer.from(body.content, "base64").toString()).toBe("x = 1\n");
  });

  it("surfaces stale-sha conflicts as errors (no silent overwrite)", async () => {
    const { repo } = client(() => new Response("conflict", { status: 409 }));
    await expect(repo.putFile("f.md", "x", "msg", "stale")).rejects.toBeInstanceOf(
      RepoClientError,
    );
  });
});

describe("getRecapFeed", () => {
  it("parses the feed JSON", async () => {
    const feed = {
      generated: "2026-06-05",
      window_hours: 24,
      accounts: {},
      topics: {},
      summary: { total_new: 0, account_lanes: 0, topic_lanes: 0 },
    };
    const { repo } = client((url) => {
      if (url.includes("compile/recap-feed.json")) {
        return Response.json({ content: b64(JSON.stringify(feed)), sha: "s" });
      }
    });
    expect(await repo.getRecapFeed()).toEqual(feed);
  });

  it("returns null when the feed doesn't exist yet", async () => {
    const { repo } = client(() => undefined);
    expect(await repo.getRecapFeed()).toBeNull();
  });
});

describe("getModelSettings", () => {
  it("parses config/models.toml", async () => {
    const { repo } = client((url) => {
      if (url.includes("config/models.toml")) {
        return Response.json({
          content: b64('[compile]\nprovider = "gemini"\n\n[recap]\nprovider = "gemini"\nmodel = "gemini-2.5-flash"\n'),
          sha: "m",
        });
      }
    });
    expect(await repo.getModelSettings()).toEqual({
      provider: "gemini",
      model: "",
      compileModel: "",
      recapModel: "gemini-2.5-flash",
    });
  });

  it("uses defaults when config/models.toml is missing", async () => {
    const { repo } = client(() => undefined);
    expect(await repo.getModelSettings()).toMatchObject({
      provider: "openai",
      model: "",
    });
  });
});

describe("listWorkflowRuns", () => {
  it("maps the runs payload to the slim shape", async () => {
    const { repo } = client((url) => {
      if (url.includes("/actions/runs")) {
        return Response.json({
          workflow_runs: [
            {
              name: "pull-bookmarks",
              status: "completed",
              conclusion: "success",
              html_url: "https://github.com/x",
              created_at: "2026-06-12T00:00:00Z",
              path: ".github/workflows/pull.yml",
              extra_field: "dropped",
            },
          ],
        });
      }
    });
    const runs = await repo.listWorkflowRuns();
    expect(runs).toEqual([
      {
        name: "pull-bookmarks",
        status: "completed",
        conclusion: "success",
        html_url: "https://github.com/x",
        created_at: "2026-06-12T00:00:00Z",
        path: ".github/workflows/pull.yml",
      },
    ]);
  });
});

describe("secrets primitives", () => {
  it("fetches the public key and PUTs sealed values", async () => {
    const { repo, calls } = client((url, init) => {
      if (url.endsWith("/actions/secrets/public-key")) {
        return Response.json({ key_id: "k1", key: "pubkey" });
      }
      if (url.includes("/actions/secrets/X_TOKENS") && init?.method === "PUT") {
        return new Response(null, { status: 201 });
      }
    });
    const key = await repo.getSecretsPublicKey();
    expect(key.key_id).toBe("k1");
    await repo.putSealedSecret("X_TOKENS", "sealed", "k1");
    const put = calls.find((c) => c.init?.method === "PUT");
    expect(JSON.parse(String(put?.init?.body))).toEqual({
      encrypted_value: "sealed",
      key_id: "k1",
    });
  });

  it("lists Actions secret names without values", async () => {
    const { repo } = client((url) => {
      if (url.endsWith("/actions/secrets?per_page=100")) {
        return Response.json({ secrets: [{ name: "X_TOKENS" }, { name: "SLACK_WEBHOOK_URL" }] });
      }
    });
    expect(await repo.listActionSecretNames()).toEqual(["X_TOKENS", "SLACK_WEBHOOK_URL"]);
  });

  it("updates an existing Actions variable", async () => {
    const { repo, calls } = client((url, init) => {
      if (url.endsWith("/actions/variables/BOWERBIRD_LIVE_INSTANCE") && init?.method === "PATCH") {
        return new Response(null, { status: 204 });
      }
    });
    await repo.putActionVariable("BOWERBIRD_LIVE_INSTANCE", "true");
    expect(calls[0].init?.method).toBe("PATCH");
    expect(JSON.parse(String(calls[0].init?.body))).toEqual({
      name: "BOWERBIRD_LIVE_INSTANCE",
      value: "true",
    });
  });

  it("creates an Actions variable when update returns 404", async () => {
    const { repo, calls } = client((url, init) => {
      if (url.endsWith("/actions/variables/BOWERBIRD_LIVE_INSTANCE") && init?.method === "PATCH") {
        return new Response("missing", { status: 404 });
      }
      if (url.endsWith("/actions/variables") && init?.method === "POST") {
        return new Response(null, { status: 201 });
      }
    });
    await repo.putActionVariable("BOWERBIRD_LIVE_INSTANCE", "true");
    expect(calls.map((call) => call.init?.method)).toEqual(["PATCH", "POST"]);
  });
});
