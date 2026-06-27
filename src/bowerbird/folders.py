"""Bookmark folder listing — the discovery step before mapping folders to topics.

The client does the network work (XBookmarkClient.folders()); this module turns the result
into the table shown by `bowerbird folders` and consumed interactively by the init wizard.
Pure over an injected client, so it's unit-testable offline.
"""
from __future__ import annotations

OWNED_READ_COST = 0.001
POST_READ_COST = 0.005


def format_folders(folders: list[dict], *, include_counts: bool = False) -> str:
    """Render [{'id', 'name'}, ...] as an aligned name/id table for terminal display."""
    if not folders:
        return "no bookmark folders found — create folders in the X app, then re-run"
    width = max(len(f.get("name", "")) for f in folders)
    header = f"{'FOLDER':<{width}}  ID"
    rows = []
    if include_counts:
        header += "  ITEMS  EST. OWNED READ  EST. POST READ"
    for folder in folders:
        row = f"{folder.get('name', ''):<{width}}  {folder.get('id', '')}"
        if include_counts:
            count = int(folder.get("count", 0))
            row += (
                f"  {count:>5}"
                f"  {format_cost(estimate_owned_read_cost(count)):>15}"
                f"  {format_cost(estimate_post_read_cost(count)):>14}"
            )
        rows.append(row)
    return "\n".join([header, *rows])


def format_cost(value: float) -> str:
    return f"${value:.3f}"


def estimate_owned_read_cost(count: int) -> float:
    return max(count, 0) * OWNED_READ_COST


def estimate_post_read_cost(count: int) -> float:
    return max(count, 0) * POST_READ_COST


def with_counts(client, folders: list[dict]) -> list[dict]:
    """Attach exact folder counts by walking ID pages.

    X does not expose a cheap total-count field for folder contents, so this
    intentionally does network reads only when the caller asks for counts.
    """
    counted = []
    for folder in folders:
        counted.append({
            **folder,
            "count": client.bookmark_count_in_folder(str(folder.get("id", ""))),
        })
    return counted


def run_folders(client, *, counts: bool = False, out=print) -> list[dict]:
    """List the authenticated user's bookmark folders; returns them for callers (wizard)."""
    folders = client.folders()
    if counts:
        folders = with_counts(client, folders)
        out(
            "counting walks each folder's ID pages; X may bill returned resources "
            "even though Bowerbird does not hydrate content here"
        )
    out(format_folders(folders, include_counts=counts))
    return folders
