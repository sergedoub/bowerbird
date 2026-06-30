#!/usr/bin/env python3
"""Generate durable recap files and runtime-agnostic delivery manifests."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from bowerbird.config import AccountsConfig, ConfigError, RecapsConfig  # noqa: E402
from bowerbird.model_config import ModelConfig, detect_setup_provider, parse_model_config  # noqa: E402
from bowerbird.recap_llm import generate_recap_body  # noqa: E402
from bowerbird.recaps import (  # noqa: E402
    RecapArtifact,
    RecapWindow,
    added_source_paths,
    build_model_prompt,
    build_recap_artifact,
    deterministic_body,
    load_source_notes,
    manifest_for,
    manifest_path,
    window_for,
)


def _parse_date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"invalid date '{value}', expected YYYY-MM-DD") from exc


def _parse_datetime(value: str) -> dt.datetime:
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"invalid datetime '{value}', expected ISO 8601 such as 2026-06-30T04:00:00Z"
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.UTC)
    return parsed.astimezone(dt.UTC)


def read_model_config() -> ModelConfig:
    path = Path(ROOT) / "config" / "models.toml"
    if not path.exists():
        return ModelConfig(provider=detect_setup_provider())
    return parse_model_config(path.read_text(encoding="utf-8"))


def account_labels() -> dict[str, str]:
    try:
        cfg = AccountsConfig.load(Path(ROOT) / "config" / "accounts.toml")
    except (FileNotFoundError, ConfigError):
        return {}
    return {
        account.handle.lower(): account.label or account.handle
        for account in cfg.accounts
    }


def read_repo_file(path: str) -> str:
    return (Path(ROOT) / path).read_text(encoding="utf-8")


def write_artifact(artifact: RecapArtifact) -> None:
    path = Path(ROOT) / artifact.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(artifact.content, encoding="utf-8")


def due_output_path(profile_name: str, window: RecapWindow) -> Path:
    return Path(ROOT) / "recaps" / profile_name / f"{window.label}.md"


def working_tree_source_paths() -> list[str]:
    import subprocess

    tracked = subprocess.run(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=A",
            "--",
            "wiki/*/sources/*.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "wiki/*/sources/*.md",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return sorted({line.strip() for line in [*tracked, *untracked] if line.strip().endswith(".md")})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog=os.environ.get("BOWERBIRD_PROG", "bowerbird recap"),
        description="Generate file-first recap Markdown artifacts and delivery manifests.",
    )
    parser.add_argument(
        "--run-date",
        type=_parse_date,
        default=None,
        help="exclusive UTC calendar end date for due recap windows (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--run-at",
        type=_parse_datetime,
        default=None,
        help="UTC moment for hourly recap windows (ISO 8601, default: now)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing recap file for the same profile/window",
    )
    parser.add_argument(
        "--deterministic",
        action="store_true",
        help="use a deterministic local body generator instead of calling the selected model",
    )
    parser.add_argument(
        "--profile",
        help="generate only one recap profile",
    )
    parser.add_argument(
        "--include-working-tree",
        action="store_true",
        help="include uncommitted new wiki source notes; useful for local acceptance before commit",
    )
    ns = parser.parse_args(argv)
    run_moment = ns.run_at or dt.datetime.now(dt.UTC)
    run_selector = ns.run_date or run_moment

    try:
        recaps_config = RecapsConfig.load(Path(ROOT) / "config" / "recaps.toml")
    except (FileNotFoundError, ConfigError) as exc:
        sys.exit(f"recap config error: {exc}")

    try:
        model = read_model_config()
    except Exception as exc:
        sys.exit(f"model config error: {exc}")

    labels = account_labels()
    path_cache: dict[tuple[str, str], list[str]] = {}
    artifacts: list[RecapArtifact] = []
    skipped_existing = 0
    skipped_empty = 0
    skipped_not_due = 0
    generated_at = dt.datetime.now(dt.UTC).isoformat(timespec="seconds")

    def synthesize(profile, prompt_text, lanes, window):
        if ns.deterministic:
            return deterministic_body(profile, prompt_text, lanes, window)
        system_prompt, user_prompt = build_model_prompt(profile, prompt_text, lanes, window)
        return generate_recap_body(model, system_prompt, user_prompt)

    for profile in recaps_config.profiles:
        if ns.profile and profile.name != ns.profile:
            skipped_not_due += 1
            continue
        window = window_for(profile, run_selector)
        if window is None:
            skipped_not_due += 1
            continue
        if due_output_path(profile.name, window).exists() and not ns.force:
            skipped_existing += 1
            continue

        cache_key = (window.start.isoformat(), window.end.isoformat())
        if cache_key not in path_cache:
            path_cache[cache_key] = added_source_paths(ROOT, window)
            if ns.include_working_tree:
                path_cache[cache_key] = sorted({
                    *path_cache[cache_key],
                    *working_tree_source_paths(),
                })
        notes = load_source_notes(
            path_cache[cache_key],
            read_repo_file,
            account_labels=labels,
        )
        artifact = build_recap_artifact(
            profile,
            notes,
            window=window,
            read_prompt=read_repo_file,
            synthesize=synthesize,
            model=model,
            generated_at=generated_at,
        )
        if artifact is None:
            skipped_empty += 1
            continue
        write_artifact(artifact)
        artifacts.append(artifact)

    if artifacts:
        hourly_labels = [
            Path(artifact.path).stem
            for artifact in artifacts
            if artifact.profile.frequency == "hourly"
        ]
        manifest_label = hourly_labels[0] if hourly_labels and len(set(hourly_labels)) == 1 else (
            ns.run_date or run_moment.date()
        )
        manifest = manifest_for(artifacts, run_date=manifest_label, generated_at=generated_at)
        path = Path(ROOT) / manifest_path(manifest_label)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(
        f"recap: generated {len(artifacts)} file(s); "
        f"skipped {skipped_not_due} not due, {skipped_existing} existing, {skipped_empty} empty"
    )


if __name__ == "__main__":
    main()
