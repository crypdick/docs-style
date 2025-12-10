from auto_docs_editor.core import expand_edit_context


def test_expand_edit_context_basic():
    content = "Line 1\nLine 2\nLine 3\nTarget\nLine 5\nLine 6\nLine 7"
    before = "Target"
    after = "Replacement"

    # Context lines = 1
    # Expected: Line 3\nTarget\nLine 5
    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=1)

    assert exp_before == "Line 3\nTarget\nLine 5\n"
    assert exp_after == "Line 3\nReplacement\nLine 5\n"


def test_expand_edit_context_start_of_file():
    content = "Target\nLine 2\nLine 3"
    before = "Target"
    after = "Replacement"

    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=1)

    assert exp_before == "Target\nLine 2\n"
    assert exp_after == "Replacement\nLine 2\n"


def test_expand_edit_context_end_of_file():
    content = "Line 1\nLine 2\nTarget"
    before = "Target"
    after = "Replacement"

    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=1)

    assert exp_before == "Line 2\nTarget"
    assert exp_after == "Line 2\nReplacement"


def test_expand_edit_context_partial_line():
    content = "Line 1\nHello Target World\nLine 3"
    before = "Target"
    after = "Replacement"

    # context_lines=0 should just expand to the full line
    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=0)

    assert exp_before == "Hello Target World\n"
    assert exp_after == "Hello Replacement World\n"

    # context_lines=1
    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=1)

    assert exp_before == "Line 1\nHello Target World\nLine 3"
    assert exp_after == "Line 1\nHello Replacement World\nLine 3"


def test_expand_edit_context_multiline_target():
    content = "Line 1\nStart\nMiddle\nEnd\nLine 5"
    before = "Start\nMiddle\nEnd"
    after = "Replaced\nBlock"

    exp_before, exp_after = expand_edit_context(content, before, after, context_lines=1)

    assert exp_before == "Line 1\nStart\nMiddle\nEnd\nLine 5"
    assert exp_after == "Line 1\nReplaced\nBlock\nLine 5"


def test_expand_edit_context_not_found():
    content = "Line 1\nLine 2"
    before = "Target"
    after = "Replacement"

    exp_before, exp_after = expand_edit_context(content, before, after)

    assert exp_before == before
    assert exp_after == after
