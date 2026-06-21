import { redirect } from "next/navigation";
import { todayUtc } from "@/lib/feed";
import { deriveHealth } from "@/lib/health";
import { repoClientFromEnv } from "@/lib/repoClient";
import { currentSession } from "@/lib/session";

export const dynamic = "force-dynamic";

const STATUS_BADGE: Record<string, string> = {
  success: "fresh",
  running: "fresh",
  failure: "stale",
  "never-ran": "stale",
};

export default async function HealthPage() {
  const session = await currentSession().catch(() => null);
  if (!session) redirect("/api/auth/login");

  const repo = repoClientFromEnv();
  const [feed, runs] = await Promise.all([repo.getRecapFeed(), repo.listWorkflowRuns(50)]);
  const health = deriveHealth(feed, runs, todayUtc());

  return (
    <>
      <h1>
        Health{" "}
        <span className={`badge ${health.ok ? "fresh" : "stale"}`}>
          {health.ok ? "healthy" : "needs attention"}
        </span>
      </h1>

      <h2>Recap feed</h2>
      <div className="lane">
        {health.feed === "missing" ? (
          <p>
            No feed yet — it appears after the first <code>kb-recap-feed</code> run.
          </p>
        ) : (
          <p>
            Generated {health.feedGenerated} · {health.totalNew} new note(s){" "}
            <span className={`badge ${health.feed === "fresh" ? "fresh" : "stale"}`}>
              {health.feed}
            </span>
            {health.feed === "stale" && (
              <span className="meta">
                {" "}
                — a stale feed usually means the cron didn&apos;t run or upstream workflows
                failed. A long-stale bookmark pull often means the X refresh token expired:
                sign in with X again to re-seed it.
              </span>
            )}
          </p>
        )}
      </div>

      <h2>Pipeline workflows (latest run)</h2>
      {health.workflows.map((w) => (
        <div className="lane" key={w.key}>
          <h3>
            {w.title}{" "}
            <span className={`badge ${STATUS_BADGE[w.status]}`}>{w.status}</span>{" "}
            {w.when && <span className="count">{w.when.slice(0, 16).replace("T", " ")} UTC</span>}
          </h3>
          {w.url && (
            <div className="meta">
              <a href={w.url}>view run on GitHub</a>
            </div>
          )}
          {w.status === "never-ran" && (
            <div className="meta">Never ran — enable Actions on your fork and dispatch it once.</div>
          )}
        </div>
      ))}
    </>
  );
}
