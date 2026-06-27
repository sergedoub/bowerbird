"""bowerbird — one CLI entry point over the bin/ scripts.

Thin by design: each verb re-execs the corresponding bin/<script>.py with the remaining
arguments, so behavior is identical to running the script directly and there is no logic
here to test (PRD: CLI routing is exempt from unit tests). The scripts locate the repo
root themselves, so verbs work from any cwd inside a checkout.

The CLI requires a repo checkout (the scripts operate on raw/, config/, wiki/ relative
to the repo root) — installing the package without the repo gives you the library only.
"""
from __future__ import annotations

import argparse
import os
import runpy
import sys
from pathlib import Path

# src/kb/cli.py -> src -> repo root (editable install / checkout layout)
ROOT = Path(__file__).resolve().parents[2]

VERBS: dict[str, tuple[str, str]] = {
    "init": ("init_wizard.py", "interactive setup: credentials, OAuth, folders, secrets"),
    "auth": ("x_auth_spike.py", "X OAuth2 flow and raw API helpers (default: auth)"),
    "folders": ("folders.py", "list your X bookmark folders (names + ids)"),
    "pull": ("pull.py", "pull new bookmarks from allowlisted folders into raw/bookmarks/"),
    "backfill": ("backfill.py", "backfill historical bookmarks with cost controls"),
    "accounts": ("accounts.py", "add or list followed X accounts"),
    "dump-account": ("dump_account.py", "mirror configured X accounts into raw/accounts/"),
    "dump-all": ("dump_all.py", "dump ALL bookmarks (every folder + unsorted) outside the pipeline"),
    "ingest-book": ("ingest_book.py", "split a configured Markdown book into raw chapters"),
    "models": ("models.py", "choose compile and recap model provider"),
    "recap": ("recap.py", "generate durable recap files and delivery manifests"),
    "slack-recap": ("slack_recap.py", "deliver generated recap files to Slack with the Bowerbird bot"),
    "push-secrets": ("push_secrets.py", "push credentials staged in bin/.env to GitHub Actions secrets"),
    "lint": ("lint.py", "run the provenance linter over wiki/"),
    "doctor": ("doctor.py", "check config, recap files, and lint status"),
}

# Verbs whose scripts parse arguments themselves (argparse) — pass --help through to
# them. Everything else gets a static synopsis here, so asking for help never starts
# the wizard, runs the linter, or requires credentials.
ARGPARSE_VERBS = {"auth", "folders", "pull", "backfill", "accounts", "dump-account",
                  "ingest-book", "models", "recap", "slack-recap", "push-secrets", "doctor"}

SYNOPSES = {
    "init": "usage: bowerbird init\n\nInteractive setup wizard: X app credentials, OAuth sign-in, bookmark-folder ->\ntopic mapping, account mirrors, GitHub Actions secrets. Re-runnable; never\noverwrites existing config without asking. Takes no arguments.",
    "lint": "usage: bowerbird lint\n\nRun the provenance and recap linter. Exits 0 and prints 'provenance and recaps OK', or\nexits 1 listing every violation. Takes no arguments.",
    "dump-all": "usage: bowerbird dump-all\n\nDump ALL bookmarks (every folder + unsorted) to ~/x-bookmarks-raw, outside the\npipeline. Requires X credentials (bin/.env). Takes no arguments.",
    "push-secrets": "usage: bowerbird push-secrets [--repo owner/name]\n\nPush credentials staged in the gitignored bin/.env (plus bin/.x_tokens.json as\nX_TOKENS) to this repo's GitHub Actions secrets via the gh CLI. Non-interactive;\nsecret values are never printed or typed.",
}


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    verb_help = "\n".join(f"  {v:<14} {desc}" for v, (_, desc) in VERBS.items())
    parser = argparse.ArgumentParser(
        prog="bowerbird",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="X bookmarks and accounts -> cited markdown wiki -> file-first recaps.",
        epilog=f"verbs:\n{verb_help}\n\nrun `bowerbird <verb> --help` for verb options",
    )
    parser.add_argument("verb", choices=sorted(VERBS), metavar="verb")
    parser.add_argument("args", nargs=argparse.REMAINDER, metavar="...")
    ns = parser.parse_args(argv)

    script = ROOT / "bin" / VERBS[ns.verb][0]
    if not script.exists():
        sys.exit(
            f"bowerbird: {script} not found — the CLI must run from a repo checkout "
            "(clone the repository, then `pip install -e .`)."
        )

    args = ns.args
    if ns.verb == "auth" and not args:
        args = ["auth"]  # bare `bowerbird auth` runs the browser OAuth flow

    wants_help = any(a in ("-h", "--help") for a in args)
    if wants_help and ns.verb not in ARGPARSE_VERBS:
        print(SYNOPSES[ns.verb])
        return

    # runpy resets argv[0] to the script path, so argparse scripts read their
    # display name (prog) from this env var instead; unset on direct runs.
    os.environ["BOWERBIRD_PROG"] = f"bowerbird {ns.verb}"
    sys.argv = [str(script)] + args
    runpy.run_path(str(script), run_name="__main__")


if __name__ == "__main__":
    main()
