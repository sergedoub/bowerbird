import HomeDashboard, { type HomeRepoState } from "./home-dashboard";
import { parseAccounts, parseTopics } from "@/lib/configModel";
import { todayUtc } from "@/lib/feed";
import { deriveHealth } from "@/lib/health";
import { authEnvStatus, buildDemoFeedPreview, deriveHomeSetup } from "@/lib/home";
import { readLocalRecapFeed } from "@/lib/localFeed";
import { defaultModelSettings, parseModelSettings } from "@/lib/modelConfig";
import { RepoClientError, repoClientFromEnv, type RepoClient } from "@/lib/repoClient";
import { currentSession } from "@/lib/session";

export const dynamic = "force-dynamic";

const TOPICS_PATH = "config/topics.toml";
const ACCOUNTS_PATH = "config/accounts.toml";
const MODELS_PATH = "config/models.toml";

export default async function Home() {
  const auth = authEnvStatus(process.env);
  const session = await currentSession().catch(() => null);
  const repo = await loadRepoState();
  const demoFeed =
    repo.kind === "ready" && repo.demoFeed
      ? repo.demoFeed
      : buildDemoFeedPreview(await readLocalRecapFeed());
  const setup = deriveHomeSetup({
    sessionUsername: session?.username ?? null,
    auth,
    repoReady: repo.kind === "ready",
    repoError: repo.kind === "error" ? repo.message : undefined,
    topics: repo.kind === "ready" ? repo.topics : [],
    accounts: repo.kind === "ready" ? repo.accounts : [],
    feed:
      repo.kind === "ready" && repo.feedGenerated
        ? {
            generated: repo.feedGenerated,
            window_hours: 24,
            accounts: {},
            topics: {},
            summary: {
              total_new: repo.feedTotalNew ?? 0,
              account_lanes: 0,
              topic_lanes: 0,
            },
          }
        : null,
    todayUtc: todayUtc(),
    healthOk: repo.kind === "ready" ? repo.healthOk : null,
  });

  return (
    <HomeDashboard
      sessionUsername={session?.username ?? null}
      auth={auth}
      setup={setup}
      repo={repo}
      demoFeed={demoFeed}
    />
  );
}

async function loadRepoState(): Promise<HomeRepoState> {
  let repo: RepoClient;
  try {
    repo = repoClientFromEnv();
  } catch (error) {
    return { kind: "error", message: errorMessage(error) };
  }

  try {
    const [topicsFile, accountsFile, modelsFile, feed] = await Promise.all([
      readOptional(repo, TOPICS_PATH),
      readOptional(repo, ACCOUNTS_PATH),
      readOptional(repo, MODELS_PATH),
      repo.getRecapFeed(),
    ]);
    const runs = await repo.listWorkflowRuns(50).catch(() => null);
    const health = runs ? deriveHealth(feed, runs, todayUtc()) : null;
    return {
      kind: "ready",
      topics: topicsFile ? parseTopics(topicsFile.content) : [],
      accounts: accountsFile ? parseAccounts(accountsFile.content) : [],
      models: modelsFile ? parseModelSettings(modelsFile.content) : defaultModelSettings(),
      topicsSha: topicsFile?.sha ?? null,
      accountsSha: accountsFile?.sha ?? null,
      modelsSha: modelsFile?.sha ?? null,
      feedGenerated: feed?.generated ?? null,
      feedTotalNew: feed?.summary.total_new ?? null,
      demoFeed: buildDemoFeedPreview(feed),
      healthOk: health?.ok ?? null,
    };
  } catch (error) {
    return { kind: "error", message: errorMessage(error) };
  }
}

async function readOptional(repo: RepoClient, path: string) {
  try {
    return await repo.getFile(path);
  } catch (error) {
    if (error instanceof RepoClientError && error.status === 404) return null;
    throw error;
  }
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}
