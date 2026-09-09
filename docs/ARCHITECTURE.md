# Architecture

Docs-style shares curated documentation rules between an agent skill and a
Python editor. The editor proposes changes to Markdown or a paired Jupyter
notebook, applies review decisions, and runs Vale before and after guide passes.

## Module map

- `skills/docs-style/`: agent workflow, curated references, Vale configuration,
  rule bundle, and lint wrapper. Plugin manifests expose this skill.
- `docs_style/core.py`: `DocumentSession`, matching, context expansion, proposal
  handling, and LangChain agent construction. It does not import the UI.
- `docs_style/controller.py`: `ReviewController` owns guide position, session,
  counters, and persistence. It imports core, notebook, and Vale adapters.
- `docs_style/workflow.py`: environment setup, input resolution, notebook
  pairing, and guide selection; returns `WorkflowContext`.
- `docs_style/core_vale.py` and `docs_style/notebook.py`: external tool adapters.
- `docs_style/tui.py` and `docs_style/widgets.py`: Textual application and review
  widgets. Worker threads hand UI operations back through `call_from_thread`.
- `docs_style/cli.py` and `main.py`: command-line entry points.
  `docs_style/tui_arguments.py` defines the TUI argument parser.
- `settings.py` and `utils.py`: checkout-relative resources, asynchronous file
  I/O, run logs, and optional Langfuse tracing.
- `bulk_pr_autodocs.py` and `crawl/`: maintenance scripts with their own PEP 723
  dependencies. The bulk script performs Git/GitHub mutations when invoked.
- `tests/`: public behavior and headless Textual interactions with external
  operations mocked. `scripts/prek_hooks/` holds source policy checks.

## Invariants

The UI imports the controller and core; core and controller never import the
UI. These are import directions, not execution order. Avoid a larger layer
framework while this package remains small.

`skills/docs-style/references/style/` is the shared source of guide content.
Guide ordering and final-pass selection belong in workflow/settings. The Python
editor operates from a checkout; it does not promise a self-contained wheel
with top-level settings and skill resources.

Review state belongs to each controller. Test state belongs to temporary
paths. No database, queue, shared port, or network service is needed for tests.
API credentials and session logs stay outside version control.

Beartype checks package functions and methods at runtime; strict mypy checks
the application and top-level support modules. Framework decorator ordering is
part of that contract. See `CONVENTIONS.md` before adding wrappers.

Revisit this map twice a year and whenever module responsibilities change.
