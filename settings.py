from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
SKILL_DIR = ROOT_DIR / "skills" / "docs-style"
STYLE_DIR = SKILL_DIR / "references" / "style"
VALE_CONFIG = SKILL_DIR / ".vale.ini"
LOGS_DIR = ROOT_DIR / "logs"
BULK_LOGS_DIR = LOGS_DIR / "bulk_pr_logs"

MODEL_NAME = "gpt-5.1"
# NOTE: README.md describes guide ordering and final-pass selection.
# --final-pass selects guide filenames whose stem ends with this marker.
FINAL_PASS_MARKER = "+"  # noqa: S105 - guide filename suffix, not a credential

DEFAULT_BASE_BRANCH = "main"
DEFAULT_REMOTE = "origin"
PR_BODY_TEMPLATE = """Apply documentation style edits with AutoDocsEditor.
These edits were generated automatically and need review.

Session log: {gist_url}
"""

CRAWLER_HEADERS = {"User-Agent": "docs-style-crawler/1.0"}
