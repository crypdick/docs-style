#!/usr/bin/env -S uv run --script
#
# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "python-dotenv>=1.0",
#   "loguru>=0.7.0",
#   "openai>=1.16.0",
#   "PyGithub>=1.59",
# ]
# ///
"""Bulk-creates draft PRs with AutoDocsEditor style edits.

For every Markdown path listed in a *greenlist* text file, this script:

1. Checks out the base branch of an **existing local clone**.
2. Creates a dedicated branch `docs/auto-edit-<slug>`.
3. Runs `auto_docs_edit.py` twice (normal + final-pass) **in YOLO mode**.
4. Opens a *secret* Gist containing the LLM session log.
5. Pushes the branch and opens a *draft* PR that links to the Gist.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from github import Github, InputFileContent
from loguru import logger

from settings import (
    AUTO_DOCS_EDIT_SCRIPT,
    BULK_LOGS_DIR,
    DEFAULT_BASE_BRANCH,
    DEFAULT_REMOTE,
    LOGS_DIR,
    PR_BODY_TEMPLATE,
    ROOT_DIR,
)

# ---------------------------------------------------------------------------
# Constants & configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR = ROOT_DIR


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def run(cmd: list[str], *, cwd: Path | None = None, capture: bool = True, dry: bool = False) -> str:
    """Execute *cmd* in *cwd* and return stdout. Raise on non-zero exit."""
    cmd_display = " ".join(cmd)
    loc = f" (cwd={cwd})" if cwd else ""
    if dry:
        logger.info(f"[dry-run] {cmd_display}{loc}")
        return ""

    logger.debug(f"$ {cmd_display}{loc}")
    try:
        result = subprocess.run(cmd, cwd=cwd, capture_output=capture, text=True, check=True)
    except subprocess.CalledProcessError as exc:
        logger.error(exc.stderr)
        raise RuntimeError(f"Command failed: {cmd_display}") from exc

    return result.stdout.strip()


def sanitize_branch_name(doc_path: Path) -> str:
    """Convert a markdown path to a git-compatible branch slug."""
    rel = str(doc_path.with_suffix(""))  # drop .md
    # Replace os separators with dash
    rel = rel.replace(os.sep, "-")
    # Slugify: keep alnum, dot, underscore, dash
    slug = re.sub(r"[^A-Za-z0-9._-]", "-", rel)
    return f"docs/auto-edit-{slug}"


def latest_session_log() -> Path:
    """Return path to the newest session.log inside logs/.*/* ."""
    if not LOGS_DIR.exists():
        raise FileNotFoundError("No logs directory produced by auto_docs_edit.py yet.")

    # Find all session.log files under logs/*/session.log
    candidates = list(LOGS_DIR.glob("*/session.log"))
    if not candidates:
        raise FileNotFoundError("session.log not found after running auto_docs_edit.py")
    # Sort by mtime
    newest = max(candidates, key=lambda p: p.stat().st_mtime)
    return newest


def repo_full_name_from_remote_url(url: str) -> str:
    """Extract owner/repo from git remote URL."""
    if url.startswith("git@"):
        # git@github.com:owner/repo.git
        seg = url.split(":", 1)[1]
    elif url.startswith("https://"):
        # https://github.com/owner/repo.git
        seg = url.split("github.com/", 1)[1]
    else:
        raise ValueError(f"Unsupported remote URL: {url}")
    seg = seg.rstrip(".git")
    return seg


# ---------------------------------------------------------------------------
# Main processing per document
# ---------------------------------------------------------------------------


def process_document(
    repo_path: Path,
    doc_rel: str,
    base_branch: str,
    remote_name: str,
    github_client: Github,
    dry_run: bool,
):
    doc_path = repo_path / doc_rel
    if not doc_path.is_file():
        raise FileNotFoundError(f"Markdown file not found: {doc_path}")

    # 1. Checkout base branch & pull
    run(["git", "checkout", base_branch], cwd=repo_path, dry=dry_run)
    run(["git", "pull", "--ff-only", remote_name, base_branch], cwd=repo_path, dry=dry_run)

    # 2. Create branch
    branch = sanitize_branch_name(Path(doc_rel))
    run(["git", "checkout", "-B", branch], cwd=repo_path, dry=dry_run)

    # 3. Run AutoDocsEditor twice
    cmd_common = ["uv", "run", "--script", str(AUTO_DOCS_EDIT_SCRIPT)]
    run(cmd_common + ["--yolo", str(doc_path)], cwd=SCRIPT_DIR, dry=dry_run)
    run(cmd_common + ["--final-pass", "--yolo", str(doc_path)], cwd=SCRIPT_DIR, dry=dry_run)

    # 4. Detect changes
    status = run(["git", "status", "--porcelain"], cwd=repo_path, dry=dry_run)
    if not status:
        logger.info("No changes produced – deleting branch and skipping PR.")
        run(["git", "checkout", base_branch], cwd=repo_path, dry=dry_run)
        run(["git", "branch", "-D", branch], cwd=repo_path, dry=dry_run)
        return

    # 5. Stage only source file(s) (avoid logs)
    run(["git", "add", doc_rel], cwd=repo_path, dry=dry_run)
    commit_msg = f"[Docs][Draft] Auto-generated style edits for {doc_rel}"
    run(["git", "commit", "-m", commit_msg], cwd=repo_path, dry=dry_run)

    # 6. Locate session.log & create gist
    log_path = latest_session_log()
    with open(log_path, encoding="utf-8") as fh:
        log_text = fh.read()

    gist_desc = f"AutoDocsEditor log – {doc_rel}"
    if dry_run:
        gist_url = "https://gist.github.com/dry-run"
    else:
        gist = github_client.get_user().create_gist(
            False,  # secret gist
            {"session.log": InputFileContent(log_text)},
            gist_desc,
        )
        gist_url = gist.html_url

    # 7. Push branch
    run(["git", "push", "-u", remote_name, branch], cwd=repo_path, dry=dry_run)

    # 8. Open draft PR
    if dry_run:
        logger.info(f"[dry-run] Would open PR for branch {branch} -> {base_branch}")
    else:
        remote_url = run(["git", "remote", "get-url", remote_name], cwd=repo_path)
        repo_full = repo_full_name_from_remote_url(remote_url)
        gh_repo = github_client.get_repo(repo_full)
        body = PR_BODY_TEMPLATE.format(gist_url=gist_url).strip()
        pr = gh_repo.create_pull(
            title=commit_msg,
            body=body,
            head=branch,
            base=base_branch,
            draft=True,
        )
        logger.success(f"Opened PR: {pr.html_url}")

    # 9. Copy session log into bulk logs dir for archive
    BULK_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    shutil.copy2(log_path, BULK_LOGS_DIR / f"{timestamp}_{branch.replace('/', '-')}.log")


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Bulk-create PRs with AutoDocsEditor edits.")
    parser.add_argument("--repo", required=True, help="Path to existing local git clone.")
    parser.add_argument(
        "--greenlist", required=True, help="Path to txt file listing markdown docs."
    )
    parser.add_argument("--base-branch", default=DEFAULT_BASE_BRANCH)
    parser.add_argument("--remote", default=DEFAULT_REMOTE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()

    # Logging setup
    BULK_LOGS_DIR.mkdir(parents=True, exist_ok=True)
    log_file = BULK_LOGS_DIR / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".log")
    logger.remove()
    logger.add(sys.stdout, level="INFO", format="{time:YYYY-MM-DD HH:mm:ss} {level}: {message}")
    logger.add(log_file, level="DEBUG", encoding="utf-8")

    # Environment
    load_dotenv()
    gh_token = os.getenv("GITHUB_TOKEN")
    if not gh_token:
        logger.error("GITHUB_TOKEN must be set in env or .env file.")
        sys.exit(1)
    github_client = Github(gh_token)

    repo_path = Path(args.repo).expanduser().resolve()
    if not (repo_path / ".git").is_dir():
        logger.error(f"{repo_path} does not appear to be a git repository.")
        sys.exit(1)

    greenlist_path = Path(args.greenlist).expanduser().resolve()
    if not greenlist_path.is_file():
        logger.error("Greenlist file not found.")
        sys.exit(1)

    with greenlist_path.open(encoding="utf-8") as fh:
        docs = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

    if not docs:
        logger.info("Greenlist is empty – nothing to do.")
        return

    logger.info(f"Processing {len(docs)} markdown documents…")

    for doc_rel in docs:
        try:
            logger.info(f"=== {doc_rel} ===")
            process_document(
                repo_path,
                doc_rel,
                args.base_branch,
                args.remote,
                github_client,
                args.dry_run,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(exc)
            if args.continue_on_error:
                logger.warning("Continuing to next document despite error…")
                continue
            else:
                sys.exit(1)

    logger.success("All documents processed.")


if __name__ == "__main__":
    main()
