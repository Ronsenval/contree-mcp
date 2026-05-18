"""Tests for the contree-cli compatible profile config."""

from __future__ import annotations

import stat
import sys
import textwrap
from pathlib import Path

import pytest

from contree_mcp.config import AuthType, Config, ConfigProfile


def _write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(body).lstrip("\n"))


@pytest.fixture(autouse=True)
def _clean_credential_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip credential env vars so host pollution can't leak into the
    resolution tests. Each test that needs an env var sets it explicitly.

    Covers the full set the resolver recognises: legacy ``CONTREE_*``
    plus the Nebius IAM ``NEBIUS_API_KEY`` / ``NEBIUS_AI_PROJECT`` pair
    that ``Config.resolve()`` treats as an explicit-token source.
    """
    for key in (
        "CONTREE_PROFILE",
        "CONTREE_TOKEN",
        "CONTREE_URL",
        "CONTREE_PROJECT",
        "NEBIUS_API_KEY",
        "NEBIUS_AI_PROJECT",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture
def config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.ini"


def test_load_iam_profile(config_path: Path) -> None:
    _write(
        config_path,
        """
        [DEFAULT]
        profile = work

        [profile:work]
        token = abc
        type = iam
        url = https://api.studio.nebius.com/sandboxes
        project = proj-1
        """,
    )
    cfg = Config(config_path)
    assert cfg.active_name == "work"
    profile = cfg["work"]
    assert profile.auth_type == AuthType.IAM
    assert profile.token == "abc"
    assert profile.project == "proj-1"


def test_load_jwt_profile_default_url_empty(config_path: Path) -> None:
    _write(
        config_path,
        """
        [profile:legacy]
        token = xyz
        type = jwt
        """,
    )
    cfg = Config(config_path)
    profile = cfg["legacy"]
    assert profile.auth_type == AuthType.JWT
    assert profile.url == ""


def test_resolve_uses_active_profile(config_path: Path) -> None:
    _write(
        config_path,
        """
        [DEFAULT]
        profile = work

        [profile:work]
        token = t1
        url = https://api.studio.nebius.com/sandboxes
        type = iam
        project = p1
        """,
    )
    cfg = Config(config_path)
    resolved = cfg.resolve()
    assert resolved.name == "work"
    assert resolved.token == "t1"
    assert resolved.project == "p1"


def test_resolve_cli_overrides(config_path: Path) -> None:
    _write(
        config_path,
        """
        [DEFAULT]
        profile = work

        [profile:work]
        token = stored
        url = https://api.studio.nebius.com/sandboxes
        type = iam
        project = stored-proj
        """,
    )
    cfg = Config(config_path)
    resolved = cfg.resolve(token="cli-token", project="cli-proj")
    assert resolved.token == "cli-token"
    assert resolved.project == "cli-proj"
    # auth_type comes from the stored profile
    assert resolved.auth_type == AuthType.IAM


def test_resolve_env_overrides(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        config_path,
        """
        [DEFAULT]
        profile = work

        [profile:work]
        token = stored
        url = https://api.studio.nebius.com/sandboxes
        type = iam
        project = stored-proj
        """,
    )
    monkeypatch.setenv("CONTREE_TOKEN", "env-token")
    monkeypatch.setenv("CONTREE_PROJECT", "env-proj")
    monkeypatch.setenv("CONTREE_URL", "https://override.example/")
    cfg = Config(config_path)
    resolved = cfg.resolve()
    assert resolved.token == "env-token"
    assert resolved.project == "env-proj"
    # trailing slash is stripped
    assert resolved.url == "https://override.example"


def test_resolve_cli_beats_env(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write(
        config_path,
        """
        [profile:work]
        token = stored
        type = iam
        project = stored
        """,
    )
    monkeypatch.setenv("CONTREE_TOKEN", "env-token")
    cfg = Config(config_path)
    resolved = cfg.resolve(profile="work", token="cli-token")
    assert resolved.token == "cli-token"


def test_resolve_unknown_profile_falls_back_to_iam_default(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CONTREE_TOKEN", "tok")
    monkeypatch.setenv("CONTREE_PROJECT", "proj")
    cfg = Config(config_path)  # config_path does not exist yet
    resolved = cfg.resolve()
    assert resolved.token == "tok"
    assert resolved.project == "proj"
    assert resolved.auth_type == AuthType.IAM
    assert resolved.url == Config.DEFAULT_IAM_URL


def test_explicit_env_token_ignores_file(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CONTREE_TOKEN+CONTREE_PROJECT in env → file profile is not consulted."""
    _write(
        config_path,
        """
        [DEFAULT]
        profile = stored

        [profile:stored]
        type = iam
        url = https://STORED.example.com
        token = STORED_TOKEN
        project = STORED_PROJECT
        """,
    )
    monkeypatch.setenv("CONTREE_TOKEN", "ENV_TOKEN")
    monkeypatch.setenv("CONTREE_PROJECT", "ENV_PROJECT")
    cfg = Config(config_path)
    resolved = cfg.resolve()

    assert resolved.name == "env"
    assert resolved.token == "ENV_TOKEN"
    assert resolved.project == "ENV_PROJECT"
    # URL is the IAM default — NOT inherited from the stored profile.
    assert resolved.url == Config.DEFAULT_IAM_URL
    assert "STORED" not in (resolved.url or "")


def test_explicit_cli_token_ignores_file(config_path: Path) -> None:
    """--token / --project on the cmdline also bypass the file."""
    _write(
        config_path,
        """
        [profile:stored]
        type = iam
        url = https://STORED.example.com
        token = STORED_TOKEN
        project = STORED_PROJECT
        """,
    )
    cfg = Config(config_path)
    resolved = cfg.resolve(token="cli-token", project="cli-proj")
    assert resolved.name == "env"
    assert resolved.token == "cli-token"
    assert resolved.project == "cli-proj"
    assert "STORED" not in (resolved.url or "")


def test_nebius_api_key_is_recognised(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NEBIUS_API_KEY / NEBIUS_AI_PROJECT are honoured as external token sources."""
    _write(
        config_path,
        """
        [profile:stored]
        type = iam
        url = https://STORED.example.com
        token = STORED_TOKEN
        project = STORED_PROJECT
        """,
    )
    monkeypatch.setenv("NEBIUS_API_KEY", "nebius-token")
    monkeypatch.setenv("NEBIUS_AI_PROJECT", "nebius-project")
    cfg = Config(config_path)
    resolved = cfg.resolve()
    assert resolved.token == "nebius-token"
    assert resolved.project == "nebius-project"
    assert resolved.auth_type == AuthType.IAM
    # CONTREE_TOKEN takes precedence over NEBIUS_API_KEY when both are set.
    monkeypatch.setenv("CONTREE_TOKEN", "contree-token")
    resolved = cfg.resolve()
    assert resolved.token == "contree-token"


def test_auth_type_arg_overrides_default(
    config_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``auth_type=AuthType.JWT`` passed to ``resolve()`` overrides the
    IAM default in the external-token bypass branch.

    With ``auth_type=IAM`` (the default), a token-only env still produces
    an IAM profile — the resulting ``ConfigProfile`` will be rejected
    later by the IAM-without-project guard in ``server.amain``. JWT mode
    must be opted into via ``--auth-type=jwt`` / parser override.
    """
    monkeypatch.setenv("CONTREE_TOKEN", "jwt-token")
    cfg = Config(config_path)

    # Default: IAM (matches `--auth-type=iam`).
    resolved_iam = cfg.resolve()
    assert resolved_iam.auth_type == AuthType.IAM
    assert resolved_iam.token == "jwt-token"
    assert resolved_iam.url == Config.DEFAULT_IAM_URL

    # JWT opt-in: no URL default, no project.
    resolved_jwt = cfg.resolve(auth_type=AuthType.JWT)
    assert resolved_jwt.auth_type == AuthType.JWT
    assert resolved_jwt.token == "jwt-token"
    assert resolved_jwt.project is None
    assert resolved_jwt.url == ""


def test_profile_repr_masks_token() -> None:
    profile = ConfigProfile(
        name="x",
        url="https://example",
        token="super-secret",
        auth_type=AuthType.IAM,
        project="p",
    )
    text = repr(profile)
    assert "super-secret" not in text
    assert "***" in text


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows reports POSIX mode as 0o666 via ACLs, not file-mode bits.",
)
def test_save_uses_restrictive_permissions(config_path: Path) -> None:
    cfg = Config(config_path)
    cfg["mine"] = ConfigProfile(
        name="mine",
        url="https://api.tokenfactory.nebius.com/sandboxes",
        token="t",
        auth_type=AuthType.IAM,
        project="p",
    )
    mode = stat.S_IMODE(config_path.stat().st_mode)
    assert mode == 0o600


def test_save_round_trip(config_path: Path) -> None:
    cfg = Config(config_path)
    cfg["mine"] = ConfigProfile(
        name="mine",
        url="https://api.studio.nebius.com/sandboxes/",
        token="t",
        auth_type=AuthType.IAM,
        project="p",
    )
    reloaded = Config(config_path)
    assert "mine" in reloaded
    assert reloaded["mine"].project == "p"
    # url trailing slash is stripped during save
    assert reloaded["mine"].url == "https://api.studio.nebius.com/sandboxes"
