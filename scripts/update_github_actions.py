"""Update pinned GitHub Actions in .github/workflows/*.yml to their latest release.

Keeps the existing "moving major tag" convention (e.g. `@v7`) when the
upstream repo publishes one pointing at the latest release, and otherwise
pins to the exact latest tag (e.g. `@v8.3.2`).
"""

from __future__ import annotations

import json
import logging
import os
import re
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT_DIR = Path(__file__).resolve().parent.parent
WORKFLOWS_DIR = PROJECT_ROOT_DIR / ".github" / "workflows"
USES_RE = re.compile(r"uses:\s*([\w.-]+/[\w.-]+)@([^\s#]+)")
VERSION_TAG_RE = re.compile(r"^v?\d+(?:\.\d+){0,2}$")

logger = logging.getLogger(__name__)


def main() -> int:
    refs: dict[str, str] = {}
    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        for repo, ref in USES_RE.findall(workflow.read_text()):
            refs.setdefault(repo, ref)

    updates: dict[str, tuple[str, str]] = {}
    for repo, current_ref in sorted(refs.items()):
        latest_ref = resolve_latest_ref(repo)
        if latest_ref is None:
            logger.warning("skip %s: no version tags found", repo)
            continue
        if latest_ref != current_ref:
            updates[repo] = (current_ref, latest_ref)

    if not updates:
        logger.info(
            "All GitHub Actions are already pinned to their latest version."
        )
        return 0

    for workflow in sorted(WORKFLOWS_DIR.glob("*.yml")):
        text = workflow.read_text()
        for repo, (old_ref, new_ref) in updates.items():
            text = text.replace(f"{repo}@{old_ref}", f"{repo}@{new_ref}")
        workflow.write_text(text)

    for repo, (old_ref, new_ref) in updates.items():
        logger.info("%s: %s -> %s", repo, old_ref, new_ref)
    return 0


def resolve_latest_ref(repo: str) -> str | None:
    latest = latest_version_tag(repo)
    if latest is None:
        return None
    major = "v" + latest.lstrip("v").split(".")[0]
    if major != latest and tag_commit(repo, major) == tag_commit(repo, latest):
        return major
    return latest


def latest_version_tag(repo: str) -> str | None:
    tags = api_get(f"/repos/{repo}/tags?per_page=100")
    versions = [t["name"] for t in tags if VERSION_TAG_RE.match(t["name"])]
    if not versions:
        return None
    return max(
        versions, key=lambda v: tuple(int(p) for p in v.lstrip("v").split("."))
    )


def tag_commit(repo: str, tag: str) -> str | None:
    try:
        ref = api_get(f"/repos/{repo}/git/ref/tags/{tag}")
    except urllib.error.HTTPError:
        return None
    return ref["object"]["sha"]


def api_get(path: str) -> object:
    request = urllib.request.Request(f"https://api.github.com{path}")
    request.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        request.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(request) as response:  # noqa: S310
        return json.load(response)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    raise SystemExit(main())
