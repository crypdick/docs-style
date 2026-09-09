# Quality scorecard

Measured on 2026-09-09 with Python 3.12 and 3.13. The application suite contains
87 tests. All pass; external LLM and tool operations are mocked. This does not
measure live model quality, service availability, or end-to-end GitHub publishing.

Combined statement and branch coverage is approximately 70%; the enforced floor is 70%.
Coverage includes every `docs_style` module, including CLI entry points. Improve
the uncovered behavior toward 100% without excluding production modules.

## Grades

Coverage grades: A >=90%, B >=80%, C >=60%, D >0%, F =0%. Type grade A means
strict mypy passes within the declared scope, not that every SDK value is free
of `Any`. Complexity grade A means all functions pass Ruff C901 at 15. Health
A means the relevant mocked tests pass; F means no direct behavior tests exist.

| Module | Coverage | Types | Complexity | Test health |
| --- | --- | --- | --- | --- |
| `core.py` | B (81%) | A | A | A |
| `core_vale.py` | A (93%) | A | A | A |
| `controller.py` | C (76%) | A | A | A |
| `notebook.py` | B (89.66%) | A | A | A |
| `workflow.py` | B (83%) | A | A | A |
| `tui.py` | C (66%) | A | A | A |
| `widgets.py` | B (85%) | A | A | A |
| `cli.py` | F (0%) | A | A | F |
| `tui_arguments.py` | D (50%, imports only) | A | A | F |

`settings.py`, `utils.py`, and `main.py` pass strict mypy and Ruff but are outside
the package coverage measurement. The PEP 723 crawler and bulk PR script are
linted; they are outside application mypy/deptry scope. The bulk script has a
mocked command regression test; the crawler has no automated behavior suite.
Source policy scripts are linted and checked with representative rejection
cases, but are outside application coverage. Tests are outside mypy scope.

## Next improvements

- Exercise CLI argument validation, guide iteration, startup failures, and
  notebook completion through public entry points.
- Cover TUI quit-button routing, write/sync failures, and terminal startup.
- Cover callback logging, out-of-band content refresh, and notebook tool discovery.
- Add live integration evaluation separately from the credential-free default suite.
- Refine dynamic callback decisions into parsed types when changing that boundary.

## Maintaining the scorecard

Run `uv run prek run --all-files`. The coverage report prints missing lines;
`htmlcov/index.html` provides source views. Update these grades after meaningful
coverage or check-scope changes, and raise `fail_under` as coverage improves.
Do not lower the floor or broaden suppressions to bypass failures.

The three secret-baseline findings are literal placeholders in `.env.SAMPLE`
and README, reviewed as non-secrets. The hook scans for additional findings.
Review tool upgrades and baseline changes explicitly. The uv dependency cooldown
is three days; the lockfile makes resolution reproducible.

Import direction is documented in `ARCHITECTURE.md` and reviewed with structural
changes. A dedicated architecture linter is deferred for this small package.
Review documentation drift with each affected feature and revisit the architecture
map twice a year. Hookify reminders require a separately installed Hookify plugin;
prek and CI enforce the mechanical rules independently.
