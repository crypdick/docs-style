---
name: taste-enforcer
enabled: true
event: prompt
pattern: don.?t use|always prefer|avoid|never do|instead of|I hate when|stop using|should always|should never|prefer .+ over|ban |forbid
action: warn
---

The prompt matched a keyword for a possible coding preference.

When the user expresses a durable coding preference, determine how to enforce
it with one of these mechanisms:

- **A prek hook script:** For code patterns that static analysis can detect,
  such as bare `except` clauses or print statements, create or update a script
  in `scripts/prek_hooks/` and configure it in `prek.toml`.

- **A Hookify rule:** For Claude's behavior during sessions, such as avoiding
  generic module names or using `NewType` for identifiers, create a rule in
  `.claude/hookify.{name}.md`. Replace `{name}` with a descriptive rule name.

- **A tool setting:** For preferences that an existing tool can enforce,
  configure the tool in `pyproject.toml`. For example, use a Ruff rule to ban
  star imports.

If an existing hook or rule already enforces the preference, investigate why
the issue occurred. Check the pattern, event type, and edge cases, then propose
a fix to strengthen the existing hook or rule.

If this hook missed a preference that the user expressed earlier in the
conversation, write a hook for that preference too.
