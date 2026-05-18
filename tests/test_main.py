"""Tests for contree_mcp.__main__ module."""

import os
import subprocess
import sys

from contree_mcp.arguments import Parser, ServerMode


class TestParser:
    """Tests for Parser argument parsing."""

    def test_parser_default_values(self) -> None:
        """Token/url/project default to None — they are resolved from config later."""
        parser = Parser()
        parser.parse_args([])
        assert parser.url is None
        assert parser.token is None
        assert parser.project is None
        assert parser.profile is None
        assert parser.mode == ServerMode.STDIO

    def test_parser_with_args(self) -> None:
        """Test Parser with command line arguments."""
        parser = Parser()
        parser.parse_args(
            [
                "--url=https://api.example.com",
                "--token=secret-token",
                "--project=proj-123",
                "--profile=staging",
                "--mode=http",
            ]
        )

        assert parser.url == "https://api.example.com"
        assert parser.token == "secret-token"
        assert parser.project == "proj-123"
        assert parser.profile == "staging"
        assert parser.mode == ServerMode.HTTP

    def test_parser_http_group(self) -> None:
        """Test Parser HTTP group settings."""
        parser = Parser()
        parser.parse_args(
            [
                "--http-listen=0.0.0.0",
                "--http-port=8000",
            ]
        )

        assert parser.http.listen == "0.0.0.0"
        assert parser.http.port == 8000

    def test_parser_cache_settings(self) -> None:
        """Test Parser cache settings."""
        parser = Parser()
        parser.parse_args(
            [
                "--cache-prune-days=30",
            ]
        )

        assert parser.cache.prune_days == 30


class TestCLI:
    """Integration tests for CLI entry point."""

    def test_cli_help(self) -> None:
        """Test that --help works and exits cleanly."""
        result = subprocess.run(
            [sys.executable, "-m", "contree_mcp", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "usage:" in result.stdout.lower() or "--help" in result.stdout

    def test_cli_missing_token_fails(self, tmp_path) -> None:
        """No token anywhere -> SystemExit with helpful message."""
        env = os.environ.copy()
        # Strip every variable the resolver treats as an explicit-token
        # source — otherwise host-level NEBIUS_API_KEY (etc.) leaks in
        # and silences the "no token" path.
        for key in (
            "CONTREE_TOKEN",
            "CONTREE_URL",
            "CONTREE_PROJECT",
            "CONTREE_PROFILE",
            "NEBIUS_API_KEY",
            "NEBIUS_AI_PROJECT",
        ):
            env.pop(key, None)
        # Point CONTREE_HOME to an empty dir so no profile is loaded.
        env["CONTREE_HOME"] = str(tmp_path)

        result = subprocess.run(
            [sys.executable, "-m", "contree_mcp"],
            capture_output=True,
            text=True,
            env=env,
        )

        assert result.returncode != 0
        assert "token" in result.stderr.lower()
