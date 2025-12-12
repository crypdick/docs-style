from unittest.mock import Mock, patch

from auto_docs_editor.core_vale import enforce_vale_style


@patch("auto_docs_editor.core_vale.shutil.which")
def test_vale_missing(mock_which, tmp_path):
    mock_which.return_value = None
    f = tmp_path / "test.md"
    f.touch()

    enforce_vale_style(f)
    # Should exit early, log error (but logs disabled)


@patch("auto_docs_editor.core_vale.shutil.which")
@patch("auto_docs_editor.core_vale.subprocess.run")
def test_vale_no_errors(mock_run, mock_which, tmp_path):
    mock_which.return_value = "/usr/bin/vale"
    mock_run.return_value.stdout = ""
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
    mock_which.return_value = "/usr/bin/vale"

    # Setup Vale output
    # First run returns error
    # Second run returns no error (to break loop)
    run1 = Mock()
    run1.stdout = "test.md:1:1:Google.Headings:Capitalization error"
    run2 = Mock()
    run2.stdout = ""
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
    mock_which.return_value = "/usr/bin/vale"
    mock_run.return_value.stdout = "test.md:1:1:Check:Error"

    f = tmp_path / "test.md"
    f.write_text("original")

    with patch("auto_docs_editor.core_vale.ChatPromptTemplate.from_template") as mock_prompt_tmpl:
        mock_chain = Mock()
        mock_chain.invoke.return_value = "PEDANTIC"
        mock_prompt_tmpl.return_value.__or__.return_value.__or__.return_value = mock_chain

        enforce_vale_style(f, max_retries=1)

        assert f.read_text() == "original"
