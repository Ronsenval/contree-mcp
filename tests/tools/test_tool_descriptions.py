"""Tests that tool docstrings and guide reference contain key UX clarifications.

These docstrings are what LLMs read as MCP tool descriptions. If a clarification
is missing, agents will misuse the tools (wrong key/value order, relative paths, etc).
"""

import inspect

from contree_mcp.resources.guide import SECTIONS
from contree_mcp.tools.download import download
from contree_mcp.tools.run import run
from contree_mcp.tools.upload import upload


class TestUploadDocstring:
    """Verify upload docstring prevents common misuse."""

    doc = upload.__doc__ or ""

    def test_mentions_local_filesystem(self) -> None:
        """Users confuse path with a destination name in storage."""
        assert "local" in self.doc.lower()

    def test_mentions_content_addressable(self) -> None:
        """Users expect uploaded files to keep their filename."""
        assert "content-addressable" in self.doc

    def test_mentions_uuid(self) -> None:
        assert "UUID" in self.doc or "uuid" in self.doc

    def test_mentions_files_param_for_naming(self) -> None:
        """Users need to know how to name a file at injection time."""
        assert "files" in self.doc


class TestRunDocstring:
    """Verify run docstring clarifies the files key/value format."""

    doc = run.__doc__ or ""

    def test_mentions_files_format(self) -> None:
        """Users swap key and value in the files dict."""
        assert "key=destination" in self.doc or "key is destination" in self.doc

    def test_shows_path_to_uuid_direction(self) -> None:
        """Docstring should show container path -> UUID mapping."""
        assert '"/path/in/container"' in self.doc or "{" in self.doc

    def test_mentions_multiple_paths(self) -> None:
        """Users should know one UUID can be mounted to multiple paths."""
        assert "multiple paths" in self.doc


class TestDownloadDocstring:
    """Verify download docstring clarifies where files go."""

    doc = download.__doc__ or ""

    def test_mentions_host_not_container(self) -> None:
        """Users confuse destination with a container path."""
        assert "not" in self.doc.lower() and "container" in self.doc.lower()

    def test_mentions_parent_directories(self) -> None:
        """Users should know parent dirs are auto-created."""
        assert "parent" in self.doc.lower() or "Parent" in self.doc

    def test_mentions_tilde_expansion(self) -> None:
        """Users should know ~ is supported."""
        assert "~" in self.doc


class TestGuideReferenceConsistency:
    """Verify the guide reference table matches actual tool signatures."""

    reference = SECTIONS["reference"]

    def test_upload_lists_all_input_params(self) -> None:
        """Guide should mention all three upload input modes."""
        assert "content" in self.reference
        assert "content_base64" in self.reference
        assert "path" in self.reference

    def test_upload_params_match_signature(self) -> None:
        """Guide should not list params that don't exist on the tool."""
        sig_params = set(inspect.signature(upload).parameters.keys())
        # The guide mentions these as upload key params
        for mentioned in ("content", "content_base64", "path"):
            assert mentioned in sig_params, f"Guide mentions '{mentioned}' but upload tool has no such param"

    def test_run_files_format_shown(self) -> None:
        """Guide should show the files format with path->uuid direction."""
        assert '"/path"' in self.reference or "{" in self.reference
        assert '"uuid"' in self.reference

    def test_run_params_match_signature(self) -> None:
        """Guide key params for run should exist on the tool."""
        sig_params = set(inspect.signature(run).parameters.keys())
        for mentioned in ("command", "image", "disposable", "wait", "files", "env", "timeout"):
            assert mentioned in sig_params, f"Guide mentions '{mentioned}' but run tool has no such param"

    def test_download_params_match_signature(self) -> None:
        """Guide key params for download should exist on the tool."""
        sig_params = set(inspect.signature(download).parameters.keys())
        for mentioned in ("image", "path"):
            assert mentioned in sig_params, f"Guide mentions '{mentioned}' but download tool has no such param"
