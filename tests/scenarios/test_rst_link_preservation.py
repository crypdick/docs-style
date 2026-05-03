"""Tests for RST-style link preservation.

RST (reStructuredText) uses backticks with double underscores for anonymous links:
    `Link Text <URL>`__

This syntax must NOT be corrupted to markdown-style bold:
    `Link Text <URL>`**

This corruption occurs when tools/LLMs misinterpret __ as bold syntax and
"normalize" it to **.
"""

import pytest

from docs_style.core import DocumentSession, expand_edit_context

# Sample RST content with anonymous links
RST_CONTENT_WITH_LINKS = """\
`Ray Data <https://docs.ray.io/en/latest/data/data.html>`__ is a
scalable framework for data processing in production.
It's built on top of `Ray <https://docs.ray.io/en/latest/index.html>`__, a
distributed computing framework.
"""

# The corrupted version (what we DON'T want)
CORRUPTED_RST_CONTENT = """\
`Ray Data <https://docs.ray.io/en/latest/data/data.html>`**is a
scalable framework for data processing in production.
It's built on top of `Ray <https://docs.ray.io/en/latest/index.html>`**, a
distributed computing framework.
"""


class TestRstLinkPreservation:
    """Tests to ensure RST-style links are preserved correctly."""

    def test_rst_link_pattern_not_corrupted_in_session(self):
        """Ensure DocumentSession doesn't corrupt RST link syntax."""
        session = DocumentSession(RST_CONTENT_WITH_LINKS, set())

        # Verify the RST links are present and intact
        assert "`__" in session.current_content, "RST link syntax should be present"
        assert "`**" not in session.current_content, "Corrupted syntax should not exist"

    def test_find_best_match_preserves_rst_links(self):
        """Test that find_best_match correctly finds RST link patterns."""
        session = DocumentSession(RST_CONTENT_WITH_LINKS, set())

        # Should find the exact RST link pattern
        rst_link = "`Ray Data <https://docs.ray.io/en/latest/data/data.html>`__"
        match = session.find_best_match(rst_link)
        assert match is not None, "Should find RST link pattern"
        assert match == rst_link, "Match should be exact"

    @pytest.mark.asyncio
    async def test_apply_edit_preserves_rst_links_in_context(self):
        """Ensure edits near RST links don't corrupt the link syntax."""
        session = DocumentSession(RST_CONTENT_WITH_LINKS, set())

        # Edit text near the RST link but not the link itself
        before = "scalable framework for data processing in production."
        after = "scalable framework for production data processing."

        result = await session.apply_edit(before, after)
        assert "successfully" in result.lower()

        # Verify RST links are still intact
        assert "`__" in session.current_content, "RST link syntax should be preserved"
        assert "`**" not in session.current_content, "RST link should not be corrupted"
        assert (
            "`Ray Data <https://docs.ray.io/en/latest/data/data.html>`__" in session.current_content
        )

    @pytest.mark.asyncio
    async def test_editing_rst_link_text_preserves_syntax(self):
        """Test editing the text inside an RST link preserves the __ suffix."""
        content = "`Old Name <https://example.com>`__ is great."
        session = DocumentSession(content, set())

        # Replace the entire link with a new one (preserving syntax)
        before = "`Old Name <https://example.com>`__"
        after = "`New Name <https://example.com>`__"

        result = await session.apply_edit(before, after)
        assert "successfully" in result.lower()
        assert "`New Name <https://example.com>`__" in session.current_content
        assert "`**" not in session.current_content

    def test_expand_edit_context_preserves_rst_links(self):
        """Ensure context expansion doesn't corrupt RST links."""
        full_content = RST_CONTENT_WITH_LINKS
        before = "scalable framework"
        after = "powerful framework"

        expanded_before, expanded_after = expand_edit_context(full_content, before, after)

        # The expanded context should include the RST link intact
        assert "`__" in expanded_before, "RST link should be in expanded context"
        assert "`**" not in expanded_before, "RST link should not be corrupted"
        assert "`**" not in expanded_after, "RST link should not be corrupted in after"

    def test_detect_rst_link_corruption(self):
        """Regression test: detect if RST links have been corrupted.

        This test explicitly checks for the known corruption pattern
        where `__ becomes `** (and sometimes loses the space after).
        """
        # This is what correct RST content looks like
        correct_patterns = [
            "`Ray Data <https://docs.ray.io/en/latest/data/data.html>`__ is",
            "`Ray <https://docs.ray.io/en/latest/index.html>`__, a",
        ]

        # This is the corrupted version we must catch
        corrupted_patterns = [
            "`Ray Data <https://docs.ray.io/en/latest/data/data.html>`**is",
            "`Ray Data <https://docs.ray.io/en/latest/data/data.html>`** is",
            "`Ray <https://docs.ray.io/en/latest/index.html>`**,",
            "`Ray <https://docs.ray.io/en/latest/index.html>`**, a",
        ]

        session = DocumentSession(RST_CONTENT_WITH_LINKS, set())

        # Verify correct patterns exist
        for pattern in correct_patterns:
            assert pattern in session.current_content, f"Expected pattern not found: {pattern}"

        # Verify corrupted patterns do NOT exist
        for pattern in corrupted_patterns:
            assert pattern not in session.current_content, f"Corrupted pattern found: {pattern}"

    @pytest.mark.asyncio
    async def test_multiple_rst_links_all_preserved(self):
        """Test that multiple RST links in a document are all preserved."""
        content = """\
See `Link1 <https://example.com/1>`__ and `Link2 <https://example.com/2>`__ for details.
Also check `Link3 <https://example.com/3>`__.
"""
        session = DocumentSession(content, set())

        # Make an edit
        await session.apply_edit("for details", "for more information")

        # Count RST link endings - should be 3
        rst_link_count = session.current_content.count("`__")
        assert rst_link_count == 3, f"Expected 3 RST links, found {rst_link_count}"

        # No corrupted patterns
        assert "`**" not in session.current_content


class TestRstLinkCorruptionDetection:
    """Utility tests for detecting RST link corruption in any content."""

    @staticmethod
    def has_corrupted_rst_links(content: str) -> bool:
        """Check if content has corrupted RST links (__ replaced with **)."""
        # Pattern: backtick followed by ** (corrupted) vs __ (correct)
        import re

        # This pattern matches the corruption: `...>`** or `...>`**<something>
        corrupted_pattern = r"`[^`]+>`\*\*"
        return bool(re.search(corrupted_pattern, content))

    @staticmethod
    def count_rst_links(content: str) -> int:
        """Count valid RST anonymous links in content."""
        import re

        # Pattern for valid RST anonymous links: `text <url>`__
        valid_pattern = r"`[^`]+<[^>]+>`__"
        return len(re.findall(valid_pattern, content))

    def test_corruption_detector_finds_corrupted_links(self):
        """Test that our corruption detector works."""
        assert self.has_corrupted_rst_links(CORRUPTED_RST_CONTENT)
        assert not self.has_corrupted_rst_links(RST_CONTENT_WITH_LINKS)

    def test_rst_link_counter(self):
        """Test RST link counting utility."""
        assert self.count_rst_links(RST_CONTENT_WITH_LINKS) == 2
        assert self.count_rst_links(CORRUPTED_RST_CONTENT) == 0  # Corrupted = not valid RST
        assert self.count_rst_links("No links here") == 0
