from unittest.mock import Mock, patch

import pytest

from auto_docs_editor.core_vale import enforce_vale_style


@patch("auto_docs_editor.core_vale.shutil.which")
def test_vale_missing(mock_which, tmp_path):
    """Test that function returns early when Vale is not installed."""
    mock_which.return_value = None
    f = tmp_path / "test.md"
    f.touch()

    # Should not raise, just return early
    enforce_vale_style(f)
    # Should exit early, log error (but logs disabled)


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
def test_vale_no_errors(mock_run, mock_which, tmp_path):
    """Test that function exits early when Vale finds no errors."""
    mock_which.return_value = "/usr/bin/vale"
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = ""
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    f = tmp_path / "test.md"
    f.touch()

    with patch("auto_docs_editor.core_vale.ChatOpenAI") as mock_llm_cls:
        enforce_vale_style(f)
        # LLM is instantiated
        mock_llm_cls.assert_called_once()
        # But not used (chain not invoked)
        # Since chain wraps llm, we can't easily check chain invoke on local var
        # But we can check if the LLM instance was invoked.
        # In langchain 0.3, it likely calls invoke/ainvoke
        mock_llm_cls.return_value.invoke.assert_not_called()


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
@patch("auto_docs_editor.core_vale.ChatOpenAI")
def test_vale_fix_applied(mock_llm_cls, mock_run, mock_which, tmp_path):
    """Test that function applies LLM fixes when Vale finds errors."""
    mock_which.return_value = "/usr/bin/vale"

    # Setup Vale output
    # First run returns error
    # Second run returns no error (to break loop)
    run1 = Mock()
    run1.returncode = 0
    run1.stdout = "test.md:1:1:Google.Headings:Capitalization error"
    run1.stderr = ""

    run2 = Mock()
    run2.returncode = 0
    run2.stdout = ""
    run2.stderr = ""

    mock_run.side_effect = [run1, run2]

    f = tmp_path / "test.md"
    f.write_text("original content")

    # Mock LLM Chain
    # The code constructs chain = prompt | llm | parser
    # It calls chain.invoke(...)
    # We can mock the invoke method on the result of the chain construction

    # This is tricky because of the pipe operator syntax.
    # But fundamentally, 'chain' is an object that has an invoke method.
    # The easiest way might be to patch ChatPromptTemplate...

    # Or actually, we can patch the constructed chain if we could access it,
    # but it's local variable.
    # The code does: chain = prompt_template | llm | StrOutputParser()

    # Mocking the components is safer.
    # We need StrOutputParser to be a pass-through or return something mockable?
    # No, StrOutputParser just parses.

    # Let's mock ChatOpenAI.
    mock_llm = mock_llm_cls.return_value

    # When chain.invoke is called, it eventually calls llm.invoke (or similar).
    # But langchain pipe logic is complex to mock via components.

    # Better approach: The chain object itself is what we invoke.
    # We can patch 'enforce_vale_style's internal chain usage? No.

    # Let's just patch ChatPromptTemplate so that __or__ returns a mock chain.
    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "fixed content"

        # prompt_template | llm | StrOutputParser -> chain
        # so mock_prompt_tmpl.return_value | ... | ... = mock_chain

        # When we do A | B, A.__or__(B) is called.
        # So we need mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=1)

        assert f.read_text() == "fixed content"


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
def test_vale_pedantic(mock_run, mock_which, tmp_path):
    """Test that function stops when LLM determines errors are pedantic."""
    mock_which.return_value = "/usr/bin/vale"
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "test.md:1:1:Check:Error"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    f = tmp_path / "test.md"
    f.write_text("original")

    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "PEDANTIC"
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=1)

        assert f.read_text() == "original"


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
def test_vale_configuration_error_exit_code_2(mock_run, mock_which, tmp_path):
    """Test that function raises RuntimeError when Vale has configuration errors (exit code 2)."""
    mock_which.return_value = "/usr/bin/vale"

    # Simulate Vale configuration error (e.g., YAML syntax error)
    mock_result = Mock()
    mock_result.returncode = 2
    mock_result.stdout = (
        "E201 Invalid value [vale_styles/Google/Commands.yml:10:1]:\ndid not find expected key"
    )
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    f = tmp_path / "test.md"
    f.write_text("# Test")

    # Should raise RuntimeError for configuration errors
    with pytest.raises(RuntimeError, match="Configuration error"):
        enforce_vale_style(f, max_retries=1)


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
def test_vale_subprocess_exception(mock_run, mock_which, tmp_path):
    """Test that function raises RuntimeError when Vale subprocess fails to execute."""
    mock_which.return_value = "/usr/bin/vale"

    # Simulate subprocess execution failure
    mock_run.side_effect = OSError("Vale binary not executable")

    f = tmp_path / "test.md"
    f.write_text("# Test")

    # Should raise RuntimeError wrapping the original exception
    with pytest.raises(RuntimeError, match="Vale execution failed"):
        enforce_vale_style(f, max_retries=1)


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
@patch("auto_docs_editor.core_vale.ChatOpenAI")
def test_vale_finds_violations_and_fixes(mock_llm_cls, mock_run, mock_which, tmp_path):
    """Test that function processes Vale violations and applies LLM fixes."""
    mock_which.return_value = "/usr/bin/vale"

    # Setup Vale output - first run finds errors, second run finds none
    run1 = Mock()
    run1.returncode = 0
    run1.stdout = "test.md:1:3:Google.We:Try to avoid using first-person plural like 'we'."
    run1.stderr = ""

    run2 = Mock()
    run2.returncode = 0
    run2.stdout = ""
    run2.stderr = ""

    mock_run.side_effect = [run1, run2]

    f = tmp_path / "test.md"
    f.write_text("# We should avoid this")

    # Mock the LLM chain
    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "# You should avoid this"
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=2)

        # Verify the fix was applied
        assert f.read_text() == "# You should avoid this"

        # Verify chain was invoked once
        mock_chain.invoke.assert_called_once()


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
@patch("auto_docs_editor.core_vale.ChatOpenAI")
def test_vale_max_retries_reached(mock_llm_cls, mock_run, mock_which, tmp_path):
    """Test that function stops after max_retries even if errors remain."""
    mock_which.return_value = "/usr/bin/vale"

    # Vale always returns errors
    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "test.md:1:1:Google.We:Error"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    f = tmp_path / "test.md"
    f.write_text("original")

    # Mock LLM to always return different content (so it keeps trying)
    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "modified"
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=2)

        # Should have been called max_retries times
        assert mock_chain.invoke.call_count == 2
        # File should have been modified
        assert f.read_text() == "modified"


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
@patch("auto_docs_editor.core_vale.ChatOpenAI")
def test_vale_llm_response_too_short(mock_llm_cls, mock_run, mock_which, tmp_path):
    """Test that function aborts if LLM response is suspiciously short."""
    mock_which.return_value = "/usr/bin/vale"

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stdout = "test.md:1:1:Google.We:Error"
    mock_result.stderr = ""
    mock_run.return_value = mock_result

    f = tmp_path / "test.md"
    original_content = "This is a long document with many words and sentences. " * 20
    f.write_text(original_content)

    # Mock LLM to return very short response (< 50% of original)
    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "short"
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=1)

        # File should NOT be modified (safety check)
        assert f.read_text() == original_content
