# Code Review Report: AutoDocsEditor

## Executive Summary

AutoDocsEditor is a well-structured Python application that uses LLMs to apply Google's style guide to documentation. The codebase demonstrates good practices in several areas but has opportunities for improvement typical of "vibe coded" projects. Overall, it's functional and has decent test coverage, but could benefit from better architecture, type safety, and error handling patterns.

---

## 🟢 What's Working Well

### 1. **Good Project Structure**

- Clear separation between CLI (`cli.py`), TUI (`tui.py`), core logic (`core.py`), and workflow (`workflow.py`)
- Proper use of a `controller.py` for state management
- Configuration centralized in `settings.py`

### 2. **Solid Testing Foundation**

- 72 tests passing ✅
- Good pytest configuration with timeouts, parallel execution, and filtering for noisy warnings
- Test helpers for Textual TUI testing in `tests/helpers/textual.py`
- Proper fixtures for mocking environment variables

### 3. **Good Tooling Setup**

- Ruff linting configured and passing
- Modern Python (3.12+) with `pyproject.toml`
- Dependencies properly managed with `uv`

### 4. **Logging Infrastructure**

- Loguru properly configured with session-based log directories
- TUI-aware logging that doesn't interfere with the display

---

## 🔴 Critical Improvements Needed

### 1. **No Type Checking Configured**

**Problem:** Despite using type hints in many places, they aren't actually verified.

Recommendation: use beartype and beartype_this_package to enforce runtime type validation.

### 2. **Inconsistent Error Handling with `sys.exit()`**

**Problem:** Functions like `setup_environment()`, `load_and_validate_target()`, and `get_style_guides()` call `sys.exit()` directly, which:

- Makes them untestable without catching `SystemExit`
- Couples business logic to CLI behavior
- Prevents reuse in library contexts

**Files affected:** `workflow.py` (lines 26, 34, 53, 78, 82), `tui.py`, `cli.py`

**Current pattern:**

```python
def setup_environment(require_api_key: bool = True) -> None:
    load_dotenv()
    if require_api_key and not os.getenv("OPENAI_API_KEY"):
        logger.error("OPENAI_API_KEY is not set...")
        sys.exit(1)  # ❌ Direct exit
```

**Recommendation:** Raise custom exceptions and handle them at the CLI boundary:

```python
class ConfigurationError(Exception):
    """Raised when required configuration is missing."""
    pass

def setup_environment(require_api_key: bool = True) -> None:
    load_dotenv()
    if require_api_key and not os.getenv("OPENAI_API_KEY"):
        raise ConfigurationError("OPENAI_API_KEY is not set...")

# In cli.py / tui.py:
try:
    setup_environment()
except ConfigurationError as e:
    logger.error(str(e))
    sys.exit(1)
```

### 3. **Mixed Sync/Async Patterns Create Complexity**

**Problem:** The codebase mixes synchronous and asynchronous code inconsistently:

- `core.py` is async
- `controller.py` has sync `run_vale()` but async `prepare_session()`
- `tui.py` uses `@work(thread=True)` for sync operations

**Files affected:** `controller.py`, `core.py`, `tui.py`

**Recommendation:** Standardize on async-first with explicit sync adapters:

```python
# In controller.py - make Vale async for consistency
async def run_vale(self) -> None:
    """Run Vale enforcement on the document."""
    await asyncio.to_thread(enforce_vale_style, self.document_path)
```

### 6. **Missing Docstrings on Key Classes**

**Problem:** Some important classes lack docstrings explaining their purpose:

**Files affected:**

- `ReviewController` in `controller.py` - has docstring ✅
- `AutoDocsEditorTUI` in `tui.py` - minimal docstring
- `DiffView` in `widgets.py` - minimal docstring

**Recommendation:** Add comprehensive docstrings:

```python
class AutoDocsEditorTUI(App):
    """Interactive terminal UI for reviewing and applying style guide edits.

    This TUI presents proposed edits one at a time, allowing the user to:
    - Accept: Apply the edit as-is
    - Modify: Edit the proposed change before applying
    - Reject: Skip the edit with an optional reason
    - Skip Guide: Move to the next style guide

    Attributes:
        controller: ReviewController managing document state and workflow
        callbacks: List of LangChain callback handlers for tracing
        ...
    """
```

### 7. **Exception Handling Could Be More Specific**

**Problem:** Broad exception handling in several places:

```python
# In tui.py line 234
except Exception:
    pass  # ❌ Silently swallowing all exceptions

# In notebook.py line 42
except Exception:
    return False  # ❌ Losing error context
```

**Recommendation:** Be specific about what exceptions you expect:

```python
except (NoMatchError, QueryError) as e:
    logger.debug(f"Query failed, continuing: {e}")
```

### 8. **Duplicate Code in CLI and TUI Entry Points**

**Problem:** Both `cli.py` and `tui.py` have similar initialization code:

```python
# Both files have:
setup_environment()
context = load_and_validate_target(args.markdown_document)
style_pages = get_style_guides(skip_through=args.skip_through, final_pass=args.final_pass)
seen_edits: set[tuple[str, str]] = set()
```

**Recommendation:** Extract shared initialization into `workflow.py`:

```python
def initialize_session(
    document_path: str,
    skip_through: str | None = None,
    final_pass: bool = False,
) -> tuple[WorkflowContext, list[Path], set[tuple[str, str]]]:
    """Initialize a document editing session."""
    setup_environment()
    context = load_and_validate_target(document_path)
    style_pages = get_style_guides(skip_through=skip_through, final_pass=final_pass)
    seen_edits: set[tuple[str, str]] = set()
    return context, style_pages, seen_edits
```

---

## 🔵 Minor Improvements

### 9. **Magic Numbers in Code**

**Problem:** Several magic numbers without explanation:

```python
# core.py
max_iterations=50  # Why 50?

# core_vale.py
len(response) < len(current_text) * 0.5  # Why 0.5?

# notebook.py
content = f.read(500)  # Why 500 chars?
```

**Recommendation:** Extract to named constants with documentation:

```python
# At module level
MAX_AGENT_ITERATIONS = 50  # Prevent runaway agent loops
CONTENT_TRUNCATION_THRESHOLD = 0.5  # Abort if response is <50% of original
METADATA_CHECK_BYTES = 500  # Enough to read jupytext frontmatter
```

### 10. **Unused Import in `core.py`**

```python
from langchain_core.callbacks import BaseCallbackHandler  # Used ✅
```

Actually, the imports look fine. But there's an issue with the fallback import pattern:

```python
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    # Fallback for newer langchain versions (1.1.0+)
    from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
```

**Problem:** This suggests uncertainty about which langchain version to target.

**Recommendation:** Pin to a specific langchain version and remove fallback complexity, or document why both are needed.

### 11. **Test File Could Use Better Organization**

**Problem:** Test files are somewhat scattered. Some are in `tests/scenarios/`, some in `tests/helpers/`, and most at the top level.

**Recommendation:** Consider organizing by feature:

```
tests/
├── conftest.py
├── core/
│   ├── test_document_session.py
│   ├── test_edit_proposal.py
│   └── test_style_guide_processing.py
├── tui/
│   ├── test_diff_view.py
│   ├── test_rejection_modal.py
│   └── test_navigation.py
├── workflow/
│   └── test_workflow.py
└── integration/
    └── test_vale_integration.py
```
