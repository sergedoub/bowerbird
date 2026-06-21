import { NextResponse } from "next/server";
import {
  type AccountEntry,
  type TopicEntry,
  ConfigValidationError,
  parseAccounts,
  parseTopics,
  serializeAccounts,
  serializeTopics,
  validateConfig,
} from "@/lib/configModel";
import {
  type ModelSettings,
  defaultModelSettings,
  parseModelSettings,
  serializeModelSettings,
  validateModelSettings,
} from "@/lib/modelConfig";
import { RepoClientError, repoClientFromEnv } from "@/lib/repoClient";
import { currentSession } from "@/lib/session";

const TOPICS_PATH = "config/topics.toml";
const ACCOUNTS_PATH = "config/accounts.toml";
const MODELS_PATH = "config/models.toml";

// GET: both configs, parsed, with shas for stale-base detection on save.
export async function GET() {
  if (!(await currentSession())) {
    return NextResponse.json({ error: "sign in first" }, { status: 401 });
  }
  const repo = repoClientFromEnv();
  const [topics, accounts, models] = await Promise.all([
    readOptional(repo, TOPICS_PATH),
    readOptional(repo, ACCOUNTS_PATH),
    readOptional(repo, MODELS_PATH),
  ]);
  return NextResponse.json({
    topics: topics ? parseTopics(topics.content) : [],
    accounts: accounts ? parseAccounts(accounts.content) : [],
    models: models ? parseModelSettings(models.content) : defaultModelSettings(),
    topicsSha: topics?.sha ?? null,
    accountsSha: accounts?.sha ?? null,
    modelsSha: models?.sha ?? null,
  });
}

// PUT: validate with the model, serialize, commit each changed file with its base sha.
// A stale sha comes back as 409 so the UI can tell the user to reload, never overwrite.
export async function PUT(req: Request) {
  if (!(await currentSession())) {
    return NextResponse.json({ error: "sign in first" }, { status: 401 });
  }
  const body = (await req.json()) as {
    topics: TopicEntry[];
    accounts: AccountEntry[];
    models: ModelSettings;
    topicsSha: string | null;
    accountsSha: string | null;
    modelsSha: string | null;
  };
  const modelProblems = validateModelSettings(body.models);
  if (modelProblems.length > 0) {
    return NextResponse.json({ problems: modelProblems }, { status: 422 });
  }
  try {
    validateConfig({ topics: body.topics, accounts: body.accounts });
  } catch (e) {
    if (e instanceof ConfigValidationError) {
      return NextResponse.json({ problems: e.problems }, { status: 422 });
    }
    throw e;
  }

  const repo = repoClientFromEnv();
  try {
    const topicsOut = await repo.putFile(
      TOPICS_PATH,
      serializeTopics(body.topics),
      "config: update topics via web app",
      body.topicsSha ?? undefined,
    );
    const accountsOut = await repo.putFile(
      ACCOUNTS_PATH,
      serializeAccounts(body.accounts),
      "config: update accounts via web app",
      body.accountsSha ?? undefined,
    );
    const modelsOut = await repo.putFile(
      MODELS_PATH,
      serializeModelSettings(body.models),
      "config: update models via web app",
      body.modelsSha ?? undefined,
    );
    return NextResponse.json({
      topicsSha: topicsOut.sha,
      accountsSha: accountsOut.sha,
      modelsSha: modelsOut.sha,
    });
  } catch (e) {
    if (e instanceof RepoClientError && (e.status === 409 || e.status === 422)) {
      return NextResponse.json(
        { error: "config changed in the repo since you loaded it — reload and re-apply" },
        { status: 409 },
      );
    }
    throw e;
  }
}

async function readOptional(repo: ReturnType<typeof repoClientFromEnv>, path: string) {
  try {
    return await repo.getFile(path);
  } catch (e) {
    if (e instanceof RepoClientError && e.status === 404) return null;
    throw e;
  }
}
