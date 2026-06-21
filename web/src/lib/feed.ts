// The recap feed contract (compile/recap-feed.json) — the stable interface between
// the pipeline and every consumer. Mirrors kb.recap_feed on the Python side.

export interface FeedNote {
  date: string;
  file: string;
  text: string;
  origin?: string;
  source_type?: string;
  raw_path?: string;
}

export interface FeedLane {
  label: string;
  total_new: number;
  notes: FeedNote[];
}

export interface RecapFeed {
  generated: string; // YYYY-MM-DD (UTC) the feed was written
  window_hours: number;
  accounts: Record<string, FeedLane>;
  topics: Record<string, FeedLane>;
  summary: {
    total_new: number;
    account_lanes: number;
    topic_lanes: number;
  };
}

/** The freshness guard: a feed is postable only on the day it was generated. */
export function isFresh(feed: RecapFeed, todayUtc: string): boolean {
  return feed.generated === todayUtc;
}

export function todayUtc(now: Date = new Date()): string {
  return now.toISOString().slice(0, 10);
}
