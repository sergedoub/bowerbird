import type { FeedLane, RecapFeed } from "@/lib/feed";
import { isFresh, todayUtc } from "@/lib/feed";
import { readLocalRecapFeed } from "@/lib/localFeed";
import { repoClientFromEnv } from "@/lib/repoClient";

export const dynamic = "force-dynamic";

function Lane({ id, lane }: { id: string; lane: FeedLane }) {
  return (
    <div className="lane">
      <h3>
        {lane.label} <span className="count">— {lane.total_new} new</span>
      </h3>
      {lane.notes.map((n) => (
        <div className="note" key={n.file}>
          <div className="meta">
            {n.date} · {n.file}
          </div>
          <p>{n.text}</p>
        </div>
      ))}
      {lane.total_new > lane.notes.length && (
        <div className="meta">
          …and {lane.total_new - lane.notes.length} more not inlined.
        </div>
      )}
    </div>
  );
}

function FeedView({ feed }: { feed: RecapFeed }) {
  const fresh = isFresh(feed, todayUtc());
  const accounts = Object.entries(feed.accounts);
  const topics = Object.entries(feed.topics);
  return (
    <>
      <p>
        Generated {feed.generated} ({feed.window_hours}h window){" "}
        <span className={`badge ${fresh ? "fresh" : "stale"}`}>
          {fresh ? "fresh" : "stale"}
        </span>
      </p>
      {feed.summary.total_new === 0 && (
        <p className="empty">A quiet day — no new source notes in the window.</p>
      )}
      {accounts.length > 0 && <h2>Accounts</h2>}
      {accounts.map(([id, lane]) => (
        <Lane key={id} id={id} lane={lane} />
      ))}
      {topics.length > 0 && <h2>Topics</h2>}
      {topics.map(([id, lane]) => (
        <Lane key={id} id={id} lane={lane} />
      ))}
    </>
  );
}

export default async function RecapPage() {
  let feed: RecapFeed | null;
  let source = "your repo";
  try {
    feed = (await repoClientFromEnv().getRecapFeed()) ?? (await readLocalRecapFeed());
  } catch (e) {
    feed = await readLocalRecapFeed();
    source = "the local demo snapshot";
    if (!feed) {
      return (
        <>
          <h1>Daily recap</h1>
          <div className="setup">
            <p>Couldn&apos;t reach your repo: {e instanceof Error ? e.message : String(e)}</p>
            <p>
              Set <code>GITHUB_REPO</code> (owner/name) and <code>GITHUB_TOKEN</code> for
              live repo reads, or keep <code>compile/recap-feed.json</code> in the local
              checkout for the demo recap.
            </p>
          </div>
        </>
      );
    }
  }
  return (
    <>
      <h1>Daily recap</h1>
      {source === "the local demo snapshot" && (
        <p className="demo-copy">Showing {source}. Connect GitHub and X to make it live.</p>
      )}
      {feed ? (
        <FeedView feed={feed} />
      ) : (
        <div className="empty">
          No <code>compile/recap-feed.json</code> in the repo yet — it appears after the
          first <code>kb-recap-feed</code> workflow run.
        </div>
      )}
    </>
  );
}
