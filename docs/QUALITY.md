# Quality scorecard

Measured on 2026-09-09 with Python 3.13. The application suite contains
97 tests. All pass with external large language model (LLM) and tool operations
mocked. These results do not measure live model quality, service availability,
or end-to-end GitHub publishing.

Combined statement and branch coverage is approximately 74%; the enforced floor is 70%.
Coverage includes every `docs_style` module, including command-line interface
(CLI) entry points. Improve coverage toward 100% without excluding production
modules.

## Grades

Coverage grades use these thresholds: A at 90%, B at 80%, C at 60%, D above 0%,
and F at 0%. Each module receives the highest grade whose threshold it meets.
Type grade A means strict mypy passes within the declared scope; values from
software development kits (SDKs) can still have the `Any` type. Complexity grade
A means all functions pass Ruff C901 with a maximum complexity of 15. Test health
grade A means the relevant mocked tests pass; F means no direct behavior tests exist.

The table compares coverage, types, complexity, and test health for each module:

| Module | Coverage | Types | Complexity | Test health |
| --- | --- | --- | --- | --- |
| `core.py` | B (81%) | A | A | A |
| `core_vale.py` | A (94%) | A | A | A |
| `controller.py` | C (76%) | A | A | A |
| `notebook.py` | B (89.66%) | A | A | A |
| `workflow.py` | B (83%) | A | A | A |
| `tui.py` | C (70%) | A | A | A |
| `widgets.py` | B (85%) | A | A | A |
| `cli.py` | D (26%) | A | A | A |
| `tui_arguments.py` | A (100%) | A | A | A |

`settings.py`, `utils.py`, and `main.py` pass strict mypy and Ruff but are outside
the package coverage measurement. The PEP 723 crawler and bulk pull request (PR)
script are linted; they are outside the application's mypy and deptry scopes.
The bulk script has a mocked command regression test; the crawler has no
automated behavior suite.
Source policy scripts are linted and checked with representative rejection
cases, but are outside application coverage. Tests are outside mypy scope.

Vale runs as a required hook on maintained Markdown files. Its execution and
configuration failures fail the check; style findings require editorial review.
The test suite uses mocks and temporary executables to verify missing-dependency
failures, editor startup, and wrapper behavior without running the real Vale binary.

## Next improvements

Improve coverage and validation with these tasks:

- Exercise CLI argument validation, guide iteration, startup failures, and
  notebook completion through public entry points.
- Cover terminal user interface (TUI) quit-button routing, write and sync
  failures, and terminal startup.
- Cover callback logging, out-of-band content refresh, and notebook tool discovery.
- Add live integration evaluation separately from the credential-free default suite.
- Refine dynamic callback decisions into parsed types when changing that boundary.

## Maintain the scorecard

Run `uv run prek run --all-files`. The coverage report prints missing lines;
`htmlcov/index.html` provides source views. Update these grades after meaningful
coverage or check-scope changes, and raise `fail_under` as coverage improves.
Do not lower the floor or broaden suppressions to bypass failures.

The three secret-baseline findings are literal placeholders in `.env.SAMPLE`
and the README file, reviewed as non-secrets. The hook scans for additional findings.
Review tool upgrades and baseline changes explicitly. The uv dependency cooldown
is three days; the lockfile makes resolution reproducible.

Review the import directions in [Architecture](ARCHITECTURE.md) when making
structural changes. The package does not use a dedicated architecture linter.
Review documentation drift with each affected feature and revisit the architecture
map twice a year. Hookify reminders require a separately installed Hookify plugin.
The prek hooks and continuous integration (CI) enforce the mechanical rules
independently.
