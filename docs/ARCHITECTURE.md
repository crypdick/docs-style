# Architecture

The docs-style project shares curated documentation rules between an agent skill and a
Python editor. The editor proposes changes to Markdown or a paired Jupyter
notebook, applies review decisions, and runs the required Vale check before and
after guide passes.

## Module map

The repository divides responsibilities among these modules and directories:

- The `skills/docs-style/` directory contains the agent workflow, curated references, Vale configuration,
  rule bundle, and lint wrapper. Plugin manifests expose this skill.
- The `docs_style/core.py` file defines `DocumentSession`, matching, context expansion, proposal
  handling, and LangChain agent construction. It does not import the user
  interface (UI).
- In the `docs_style/controller.py` file, `ReviewController` owns guide position, session,
  counters, and persistence. It imports core, notebook, and Vale adapters.
- The `docs_style/workflow.py` file handles environment setup, input resolution, notebook
  pairing, and guide selection, and returns `WorkflowContext`. Environment setup
  rejects a missing Vale executable before loading or pairing documents.
- The `docs_style/core_vale.py` and `docs_style/notebook.py` files provide external tool adapters.
- The `docs_style/tui.py` and `docs_style/widgets.py` files define the Textual app and review
  widgets. Worker threads hand UI operations back through `call_from_thread`.
- The `docs_style/cli.py` and `main.py` files define command-line entry points.
  The `docs_style/tui_arguments.py` file defines the terminal user interface (TUI)
  argument parser.
- The `settings.py` and `utils.py` files provide checkout-relative resources, asynchronous file
  input/output (I/O), run logs, and optional Langfuse tracing.
- The `bulk_pr_autodocs.py` file and `crawl/` directory contain maintenance scripts
  with their own inline dependency declarations. The bulk script changes Git and GitHub state when invoked.
- The `tests/` directory contains tests of public behavior and headless Textual
  interactions with external operations mocked. The `scripts/prek_hooks/` directory
  holds source policy checks.

## Invariants

The UI imports the controller and core. Core and controller never import the
UI. These are import directions, not execution order. Avoid a larger layer
framework while this package remains small.

`skills/docs-style/references/style/` is the shared source of guide content.
Guide ordering and final-pass selection belong in the `workflow.py` and `settings.py` files.
The Python editor operates from a checkout. A self-contained wheel with
top-level settings and skill resources is not guaranteed.

Review state belongs to each controller. Test state belongs to temporary
paths. Tests require no database, queue, shared port, or network service.
API credentials and session logs stay outside version control.

Beartype checks package functions and methods at run time. Strict mypy checks
the application and top-level support modules. Framework decorator ordering is
part of that contract. See [Design conventions](../CONVENTIONS.md) before adding
wrappers.

Revisit this map twice a year and whenever module responsibilities change.
