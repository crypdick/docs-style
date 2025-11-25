from pathlib import Path

# ---------------------------------------------------------------------------
# Paths & Configuration
# ---------------------------------------------------------------------------

ROOT_DIR = Path(__file__).resolve().parent
STYLE_DIR = ROOT_DIR / "style"
LOGS_DIR = ROOT_DIR / "logs"
BULK_LOGS_DIR = LOGS_DIR / "bulk_pr_logs"
AUTO_DOCS_EDIT_SCRIPT = ROOT_DIR / "auto_docs_edit.py"

# ---------------------------------------------------------------------------
# Auto Docs Edit Settings
# ---------------------------------------------------------------------------

MODEL_NAME = "o4-mini"  # "gpt-4.1-mini"
DIFF_END_MARKER = "NO_CHANGES"
# Symbol that marks a style-guide Markdown file as relevant for the
# "final pass" mode (see --final-pass CLI flag). Any file whose **stem**
# ends with this character will be included when --final-pass is used.
FINAL_PASS_MARKER = "+"

DIFF_SYSTEM_PROMPT = (
    "You are an expert technical editor. "
    "Given a STYLE GUIDE and a MARKDOWN DOCUMENT (each provided inside their own XML tags), propose the MINIMAL set of textual edits needed "
    "for the document to follow the guide. Output the edits in STRICT XML using the following template *repeated* "
    "once per edit (do not add attributes, comments, or any other markup):\n\n"
    "<edit>\n"
    "<before>PASTE UNCHANGED TEXT EXACTLY AS IT APPEARS (may span multiple lines)</before>\n"
    "<after>REPLACEMENT TEXT EXACTLY AS IT SHOULD APPEAR (may span multiple lines)</after>\n"
    "<reason>BRIEF (~25 words) SUMMARY OF THE RELEVANT STYLE-GUIDE RULE</reason>\n"
    "</edit>\n\n"
    "IMPORTANT: Be extremely careful when authoring the <before> snippet—"
    "it must match the document text *character-for-character*, including whitespace and newlines. "
    "It is not necessary to wrap the contents of <before> or <after> with quotation marks or other wrapping characters in order to match the source text. "
    "For example, to match the text 'Hello, world!', use <before>Hello, world!</before> not <before>'\nHello, world!\n'</before>."
    "If it is not an exact match, applying the diff will fail with an error.\n"
    "You do NOT need to pad the snippet with surrounding context; matching the smallest distinctive substring is sufficient, as long as it uniquely identifies the text to change.\n"
    "The STYLE GUIDE will be supplied inside <style_guide>…</style_guide> and the DOCUMENT inside <document>…</document>. "
    "Only modify the DOCUMENT—never the STYLE GUIDE. "
    "Do NOT remove or alter Markdown anchor tags or link identifiers such as '[](){ #anchor-id }' (and similar inline anchor syntaxes). "
    "Separate <edit> blocks only by whitespace/newlines—no other text. If several identical snippets require the same "
    "replacement, output ONE <edit> block for them. If the style guide does NOT apply, respond with exactly "
    f"'{DIFF_END_MARKER}'.  Do NOT output anything else. "
    "Never output an <edit> block whose <before> and <after> content are identical. "
    "These are a NO-OP and should be discarded. "
    "Each <edit> MUST remain small and local: the <before> snippet should not exceed 10 lines of text or ~300 characters. "
    "If the required change spans more than this limit, break it into multiple <edit> blocks, one per contiguous section. "
    "This is because if there are any mistake in the diff, it will fail to apply."
    " Preserve the existing wording, tone, and sentence structure unless the STYLE GUIDE explicitly requires a change or the text contains an unequivocal error (spelling, grammar, punctuation). "
    "Avoid making subjective rephrasings or stylistic rewrites not mandated by the STYLE GUIDE. "
    "Example 1: if the style guide is about correct usage of parenthesis, do not make edits that change usage of capitalization, punctuation, or other style rules."
    "Example 2: if the style guide is about tone, do not make edits that change how contractions are used."
    "Inside fenced (```\n...\n```) or indented code blocks, only make edits that are guaranteed to keep the code syntactically valid for its language. "
    "If applying a grammar or style rule could break, invalidate, or change the meaning of the code, skip that edit entirely. "
    "When several corrections are possible, prefer the one that achieves compliance with the least amount of change."
    " If a literal application of the STYLE GUIDE produces text that reads awkwardly, stilted, or unclear, exercise editorial judgment and rephrase the passage so it remains natural, readable, and faithful to the original meaning while still honoring the spirit of the guideline. Prioritize clarity and smooth prose over mechanical adherence when necessary."
)

# ---------------------------------------------------------------------------
# Bulk PR Settings
# ---------------------------------------------------------------------------

DEFAULT_BASE_BRANCH = "main"
DEFAULT_REMOTE = "origin"

PR_BODY_TEMPLATE = """Testing Auto Docs Editor in YOLO mode for Douglas.
The diff was automatically generated and needs to be reviewed by Douglas.

Session log: {gist_url}
"""

# ---------------------------------------------------------------------------
# Crawler Settings
# ---------------------------------------------------------------------------

CRAWLER_HEADERS = {"User-Agent": "markdown-crawler/1.0 (+https://github.com/ray-project)"}
