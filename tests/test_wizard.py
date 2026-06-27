"""Init wizard: full flow with scripted I/O and fake collaborators — no network, no files.

Tests drive the wizard exactly as a user would (answer by answer) and assert on the
artifacts: env writes, config writes, secrets pushed, remaining-steps checklist.
"""
import tomllib

from bowerbird.wizard import WizardDeps, WizardIO, accounts_toml, recaps_toml, run_wizard, topics_toml


class FakeWorld:
    """All WizardDeps edges backed by in-memory state."""

    def __init__(self, *, folders=None, gh=True, tokens="", oauth_ok=True,
                 env=None, configs=None):
        self.folders = folders or []
        self.gh = gh
        self.tokens = tokens
        self.oauth_ok = oauth_ok
        self.env = dict(env or {})
        self.configs = dict(configs or {})
        self.secrets = {}
        self.variables = {}
        self.oauth_runs = 0

    def deps(self) -> WizardDeps:
        def oauth_flow():
            self.oauth_runs += 1
            if self.oauth_ok:
                self.tokens = '{"access_token": "at", "refresh_token": "rt"}'
            return self.oauth_ok

        class Client:
            def __init__(self, folders):
                self._folders = folders

            def folders(self):
                return self._folders

        return WizardDeps(
            oauth_flow=oauth_flow,
            load_tokens=lambda: self.tokens,
            make_folder_client=lambda: Client(self.folders),
            gh_available=lambda: self.gh,
            set_secret=lambda n, v: self.secrets.__setitem__(n, v) or True,
            set_variable=lambda n, v: self.variables.__setitem__(n, v) or True,
            read_env=lambda: dict(self.env),
            write_env=lambda e: self.env.update(e),
            read_config=lambda name: self.configs.get(name, ""),
            write_config=lambda name, text: self.configs.__setitem__(name, text),
        )


def scripted_io(answers):
    answers = list(answers)
    transcript = []

    def ask(prompt):
        transcript.append(prompt)
        return answers.pop(0) if answers else ""

    return WizardIO(ask=ask, say=transcript.append), transcript


def test_happy_path_writes_configs_and_secrets():
    world = FakeWorld(folders=[{"id": "111", "name": "Marketing"},
                               {"id": "222", "name": "Memes"}])
    io, transcript = scripted_io([
        "client-id", "client-secret", "bearer-tok",   # step 1 credentials
        "marketing",                                  # folder 111 -> topic
        "",                                           # folder 222 skipped
        "account_one", "ai-updates",                  # one mirrored account
        "",                                           # finish accounts
        "", "",                                      # create daily marketing recap
        "",                                           # create daily account recap
        "", "",                                      # OpenAI provider, provider default model
        "pat-token",                                  # GH_PAT
        "openai-key",                                 # OPENAI_API_KEY
    ])
    result = run_wizard(io, world.deps())

    assert result.topics == {"marketing": ["111"]}
    parsed = tomllib.loads(world.configs["topics.toml"])
    assert parsed["topics"]["marketing"]["folder_ids"] == ["111"]

    parsed_accounts = tomllib.loads(world.configs["accounts.toml"])
    assert parsed_accounts["handles"][0] == {
        "handle": "account_one", "topic": "ai-updates", "off_topic": "skip"}

    parsed_recaps = tomllib.loads(world.configs["recaps.toml"])
    assert parsed_recaps["recaps"][0]["name"] == "marketing-daily"
    assert parsed_recaps["recaps"][0]["topics"] == ["marketing"]
    assert parsed_recaps["recaps"][1]["name"] == "accounts-daily"
    assert parsed_recaps["recaps"][1]["accounts"] == ["account_one"]

    assert world.env["X_CLIENT_ID"] == "client-id"
    assert world.env["COMPILE_RUNNER"] == "codex"
    assert tomllib.loads(world.configs["models.toml"])["model"]["provider"] == "openai"
    assert world.oauth_runs == 1
    assert set(world.secrets) == {"X_CLIENT_ID", "X_CLIENT_SECRET", "X_BEARER_TOKEN",
                                  "X_TOKENS", "GH_PAT", "OPENAI_API_KEY"}
    assert world.secrets["X_TOKENS"] == world.tokens
    assert world.variables == {"BOWERBIRD_LIVE_INSTANCE": "true"}
    assert result.remaining == []


def test_comment_only_config_templates_do_not_block_init_generation():
    world = FakeWorld(
        folders=[{"id": "111", "name": "Marketing"}],
        configs={
            "topics.toml": "# Bookmark folders -> wiki topics.\n",
            "accounts.toml": "# X accounts to mirror.\n",
            "recaps.toml": "# Active recap profiles.\n",
            "models.toml": "# Model provider.\n",
        },
    )
    io, transcript = scripted_io([
        "client-id", "client-secret", "bearer-tok",
        "marketing",
        "account_one", "ai-updates",
        "",
        "", "",
        "",
        "", "",
        "pat-token",
        "openai-key",
    ])
    result = run_wizard(io, world.deps())

    assert result.topics == {"marketing": ["111"]}
    assert result.accounts == [{"handle": "account_one", "topic": "ai-updates"}]
    assert [profile["name"] for profile in result.recaps] == ["marketing-daily", "accounts-daily"]
    assert "Replace it with" not in "\n".join(transcript)
    assert tomllib.loads(world.configs["recaps.toml"])["recaps"][0]["topics"] == ["marketing"]


def test_no_gh_prints_manual_secret_values():
    world = FakeWorld(gh=False, folders=[{"id": "111", "name": "m"}])
    io, transcript = scripted_io([
        "cid", "", "bearer",
        "marketing",
        "",       # finish accounts
        "", "",  # create daily marketing recap
        "", "",     # OpenAI provider, provider default model
        "", "",      # skip GH_PAT + OPENAI_API_KEY
    ])
    result = run_wizard(io, world.deps())
    assert world.secrets == {}
    joined = "\n".join(transcript)
    assert "X_CLIENT_ID = cid" not in joined
    assert "secret X_CLIENT_ID" in joined
    assert "config/models.toml records the selected model provider" in joined
    assert any("X_BEARER_TOKEN" in r for r in result.remaining)
    assert any("GH_PAT" in r for r in result.remaining)


def test_rerun_does_not_clobber_configs_without_consent():
    world = FakeWorld(
        folders=[{"id": "999", "name": "new"}],
        tokens='{"access_token": "kept"}',
        configs={"topics.toml": '[topics.existing]\nfolder_ids = ["1"]\n',
                 "accounts.toml": '[[handles]]\nhandle = "kept"\ntopic = "t"\n'},
        env={"X_CLIENT_ID": "saved-id"},
    )
    io, _ = scripted_io([
        "", "", "",   # keep saved credentials
        "n",          # don't re-run OAuth (tokens already saved)
        "n",          # don't replace topics.toml
        "n",          # don't replace accounts.toml
        "", "",      # OpenAI provider, provider default model
        "", "",       # skip GH_PAT + OPENAI_API_KEY
    ])
    result = run_wizard(io, world.deps())
    assert world.oauth_runs == 0
    assert "existing" in world.configs["topics.toml"]
    assert "kept" in world.configs["accounts.toml"]
    assert result.topics == {} and result.accounts == []
    assert world.env["X_CLIENT_ID"] == "saved-id"


def test_failed_oauth_degrades_to_manual_folder_ids_and_checklist():
    world = FakeWorld(oauth_ok=False)
    io, _ = scripted_io([
        "cid", "", "bearer",
        "12345", "marketing",   # manual folder id entry
        "",                      # finish folder ids
        "",                      # finish accounts
        "", "",                  # create daily marketing recap
        "", "",                  # OpenAI provider, provider default model
        "", "",                  # skip GH_PAT + OPENAI_API_KEY
    ])
    result = run_wizard(io, world.deps())
    assert result.topics == {"marketing": ["12345"]}
    assert any("bowerbird auth" in r for r in result.remaining)


def test_folder_listing_failure_falls_back_to_manual_entry():
    world = FakeWorld()

    class Boom:
        def folders(self):
            raise RuntimeError("api down")

    deps = world.deps()
    deps.make_folder_client = lambda: Boom()
    io, _ = scripted_io([
        "cid", "", "bearer",
        "777", "ai",
        "",       # finish folder ids
        "",       # finish accounts
        "", "",
        "", "",
        "", "",
    ])
    result = run_wizard(io, deps)
    assert result.topics == {"ai": ["777"]}


def test_staged_secrets_in_env_file_flow_through_on_enter():
    # An agent with browser control stages Copy-button credentials in bin/.env;
    # the wizard must offer them as saved defaults and push them as secrets.
    world = FakeWorld(
        folders=[{"id": "111", "name": "m"}],
        env={"X_CLIENT_ID": "cid", "X_CLIENT_SECRET": "csec", "X_BEARER_TOKEN": "bearer",
             "GH_PAT": "staged-pat", "OPENAI_API_KEY": "staged-openai"},
    )
    io, transcript = scripted_io([
        "", "", "",     # keep staged credentials
        "marketing",    # folder 111 -> topic
        "",             # finish accounts
        "", "",        # create daily marketing recap
        "", "",        # OpenAI provider, provider default model
        "",             # Enter keeps staged GH_PAT
        "",             # Enter keeps staged OPENAI_API_KEY
    ])
    result = run_wizard(io, world.deps())
    assert world.secrets["GH_PAT"] == "staged-pat"
    assert world.secrets["OPENAI_API_KEY"] == "staged-openai"
    assert result.remaining == []
    assert any("saved value found" in str(t) for t in transcript)


def test_toml_writers_emit_valid_toml():
    topics = tomllib.loads(topics_toml({"a-b": ["1", "2"], "c": ["3"]}))
    assert topics["topics"]["a-b"]["folder_ids"] == ["1", "2"]
    accounts = tomllib.loads(accounts_toml([{"handle": "h", "topic": "t"}]))
    assert accounts["handles"][0]["off_topic"] == "skip"
    labeled = tomllib.loads(accounts_toml([{"handle": "h", "topic": "t", "label": "Handle"}]))
    assert labeled["handles"][0]["label"] == "Handle"
    recaps = tomllib.loads(recaps_toml([{"name": "marketing-weekly", "frequency": "weekly",
                                         "topics": ["marketing"]}]))
    assert recaps["recaps"][0]["weekly_due_day"] == "monday"
