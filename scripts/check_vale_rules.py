"""Run deterministic integration checks against the bundled rules and real Vale."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_CASES = [
    ("WordList", "Use OAuth 2.0 authentication.", "Use OAuth 2 authentication."),
    ("WordList", "Use OAuth 2.0 authentication.", "Use OAuth2 authentication."),
    ("WordList", "Use OAuth 2.0 authentication.", "Use OAuth2.0 authentication."),
    ("WordList", "Use OAuth 2.0 authentication.", "Use Oauth authentication."),
    ("ProductTerms", "Use OAuth 2.0 authentication.", "Use OAuth 2 authentication."),
    ("ProductTerms", "Use OAuth 2.0 authentication.", "Use OAuth2 authentication."),
    ("ProductTerms", "Use OAuth 2.0 authentication.", "Use OAuth2.0 authentication."),
    ("ProductTerms", "Use OAuth 2.0 authentication.", "Use Oauth authentication."),
    ("WordList", "Complete single sign-on.", "Complete sign-on."),
    ("WordList", "Single sign-on is required.", "Use single signon."),
    ("WordList", "Complete single\nsign-on.", "Use single\nsignon."),
    ("WordList", "Email sends a notification.", "Send Email to users."),
    ("WordList", "Email, text, and calls work.", "Send e-mail to users."),
    ("WordList", "Save it. Email the report.", "E-mail the report."),
    ("WordList", "Save it! Email the report.", "Send Email to users."),
    ("WordList", "Save it? Email the report.", "Send Email to users."),
    ("WordList", "Save it.\nEmail the report.", "Send Email to users."),
    (
        "Acronyms",
        "Use role-based access control (RBAC). RBAC protects it.",
        "RBAC protects it.",
    ),
    (
        "Acronyms",
        "Use role-based\naccess control (RBAC). RBAC protects it.",
        "RBAC protects it.",
    ),
    (
        "Acronyms",
        "Use time-based one-time password (TOTP) values. TOTP expires.",
        "TOTP expires.",
    ),
    (
        "Clarity",
        "| Type | Meaning |\n| --- | --- |\n| String | Text |",
        "| Step |\n| --- |\n| Type your name. |",
    ),
    ("Clarity", "The write is high-impact.", "The change will impact users."),
    ("Clarity", "Read a type-check result.", "Type your name in the field."),
    ("Verbs", "The write is high-impact.", "The change impacts users."),
    ("TechnicalTerms", "Send plain text messages.", "Perform data cleansing."),
    ("TechnicalTerms", "Encrypt the plaintext.", "Use a MIME type."),
    ("Colons", "Thread lookup: Discord can find it.", "Thread lookup: Requests can fail."),
    ("Colons", "The format: HTTP is supported.", "The format: Text is supported."),
    ("Colons", "The token is urn:example: Value.", "The token: Value is required."),
]


def _lint(text: str, config: Path) -> list[dict[str, object]]:
    vale = shutil.which("vale")
    if vale is None:
        raise RuntimeError("Run with uv run --locked to use the required Vale dependency")
    result = subprocess.run(
        [vale, "--no-global", f"--config={config}", "--no-exit", "--output=JSON", "--ext=.md"],
        input=text,
        text=True,
        capture_output=True,
        check=True,
        timeout=15,
    )
    return [alert for alerts in json.loads(result.stdout).values() for alert in alerts]


def main() -> int:
    """Exercise Markdown parsing, vocabulary, matches, and rendered diagnostics."""
    failures: list[str] = []
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        styles = root / "styles"
        shutil.copytree(_ROOT / "skills/docs-style/vale_styles/Google", styles / "Google")
        vocab = styles / "config/vocabularies/Regression"
        vocab.mkdir(parents=True)
        (vocab / "accept.txt").write_text("Discord\nHTTP\n", encoding="utf-8")
        config = root / ".vale.ini"
        config.write_text(
            "StylesPath = styles\nVocab = Regression\nMinAlertLevel = suggestion\n"
            "[*.md]\nBasedOnStyles = Google\n",
            encoding="utf-8",
        )
        for rule, accepted, violation in _CASES:
            check = f"Google.{rule}"
            if check in {alert["Check"] for alert in _lint(accepted, config)}:
                failures.append(f"{check} incorrectly flags {accepted!r}")
            if check not in {alert["Check"] for alert in _lint(violation, config)}:
                failures.append(f"{check} missed {violation!r}")
        messages = [
            alert["Message"]
            for alert in _lint("Ask a guru.", config)
            if alert["Check"] == "Google.InclusiveTerms"
        ]
        if messages != ["Use 'expert' or 'teacher' instead of 'guru'."]:
            failures.append(
                f"Google.InclusiveTerms has incorrect replacement messages: {messages!r}"
            )
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"Passed {len(_CASES)} accepted/invalid pairs and replacement-message check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
