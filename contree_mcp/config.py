"""Profile-based configuration compatible with contree-cli.

Reads the same ``auth.ini`` that ``contree auth`` writes, so a single
authentication is enough for both tools. Layout:

* ``$CONTREE_HOME`` / ``$XDG_CONFIG_HOME/contree`` / ``~/.config/contree``
* ``auth.ini`` — profile credentials, 0o600
"""

from __future__ import annotations

import configparser
import logging
import os
import stat
from collections.abc import Iterator, MutableMapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

log = logging.getLogger(__name__)


def _get_default_path(env: str, default: str | Path) -> Path:
    return Path(os.getenv(env) or default).expanduser()


XDG_CONFIG_HOME = _get_default_path("XDG_CONFIG_HOME", "~/.config")
CONTREE_HOME = _get_default_path("CONTREE_HOME", XDG_CONFIG_HOME / "contree")
CONFIG_DIR = CONTREE_HOME
CONFIG_FILE = CONTREE_HOME / "auth.ini"


class AuthType(str, Enum):
    IAM = "iam"
    JWT = "jwt"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True, repr=False)
class ConfigProfile:
    name: str
    url: str
    token: str | None
    auth_type: AuthType = AuthType.JWT
    project: str | None = None

    def __repr__(self) -> str:
        masked = "***" if self.token else None
        return (
            f"{self.__class__.__name__}(name={self.name!r}, url={self.url!r},"
            f" token={masked!r}, auth_type={self.auth_type!r},"
            f" project={self.project!r})"
        )


class Config(MutableMapping[str, ConfigProfile]):
    """Read-only-ish view over the contree-cli INI config.

    Mirrors :class:`contree_cli.config.Config` so users can run
    ``contree auth`` once and have the MCP server pick the credentials up.
    Writing is supported but normally the CLI manages the file.
    """

    DEFAULT_IAM_URL = "https://api.tokenfactory.nebius.com/sandboxes"
    PROFILE_PREFIX = "profile:"

    def __init__(self, path: Path | None = None) -> None:
        self.__path = path or CONFIG_FILE
        self.__profiles: dict[str, ConfigProfile] = {}
        self.__active: str = "default"
        self._load()

    def _load(self) -> None:
        cp = configparser.ConfigParser()
        log.debug("Loading config from %s", self.__path)
        cp.read(self.__path)
        self.__active = cp.defaults().get("profile", "default")
        self.__profiles.clear()
        for section in cp.sections():
            if section.startswith(self.PROFILE_PREFIX):
                p = self._parse_profile(cp, section)
                self.__profiles[p.name] = p

    @classmethod
    def _parse_profile(
        cls,
        cp: configparser.ConfigParser,
        section: str,
    ) -> ConfigProfile:
        auth_type = AuthType(cp.get(section, "type", fallback=AuthType.JWT.value))
        default_url = cls.DEFAULT_IAM_URL if auth_type == AuthType.IAM else ""
        return ConfigProfile(
            name=section[len(cls.PROFILE_PREFIX) :],
            token=cp.get(section, "token", fallback=None),
            url=cp.get(section, "url", fallback=default_url),
            auth_type=auth_type,
            project=cp.get(section, "project", fallback=None),
        )

    def _save(self) -> None:
        cp = configparser.ConfigParser()
        cp["DEFAULT"]["profile"] = self.__active
        for profile in self.__profiles.values():
            section = self.PROFILE_PREFIX + profile.name
            cp.add_section(section)
            if profile.token is not None:
                cp.set(section, "token", profile.token)
            cp.set(section, "url", profile.url.rstrip("/"))
            cp.set(section, "type", str(profile.auth_type))
            if profile.project is not None:
                cp.set(section, "project", profile.project)
        self.__path.parent.mkdir(parents=True, exist_ok=True)
        # 0o600 from the start: never world/group readable, even between
        # create() and chmod().
        fd = os.open(
            self.__path,
            os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
            stat.S_IRUSR | stat.S_IWUSR,
        )
        with os.fdopen(fd, "w") as f:
            cp.write(f)
        os.chmod(self.__path, stat.S_IRUSR | stat.S_IWUSR)

    def __contains__(self, name: object) -> bool:
        return name in self.__profiles

    def __getitem__(self, name: str) -> ConfigProfile:
        return self.__profiles[name]

    def __setitem__(self, name: str, profile: ConfigProfile) -> None:
        assert name == profile.name, "profile name must match key"
        self.__profiles[name] = profile
        self._save()

    def __delitem__(self, name: str) -> None:
        if name not in self.__profiles:
            raise KeyError(name)
        self.__profiles.pop(name)
        if self.__active == name:
            self.__active = next(iter(self.__profiles), "default")
        self._save()

    def __len__(self) -> int:
        return len(self.__profiles)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__profiles)

    @property
    def active_name(self) -> str:
        return self.__active

    def resolve(
        self,
        *,
        profile: str | None = None,
        token: str | None = None,
        url: str | None = None,
        project: str | None = None,
        auth_type: AuthType = AuthType.IAM,
    ) -> ConfigProfile:
        """Resolve credentials.

        Resolution rules:

        1. If a token is supplied externally — via ``--token``,
           ``CONTREE_TOKEN``, or ``NEBIUS_API_KEY`` — the profile file is
           **ignored entirely**. ``url``, ``project`` and ``auth_type``
           come from explicit CLI flags, the matching env vars
           (``CONTREE_URL`` / ``CONTREE_PROJECT`` / ``NEBIUS_AI_PROJECT``),
           or sensible defaults. The resolved profile gets the synthetic
           name ``"env"``. This makes env-driven setups deterministic and
           lets hot-reload skip a file it would never consult.

        2. Otherwise, the active profile from ``auth.ini`` is the source
           of truth. The profile name comes from the ``profile`` argument
           > ``CONTREE_PROFILE`` env > the file's ``[DEFAULT] profile``
           line.

        The ``NEBIUS_API_KEY`` / ``NEBIUS_AI_PROJECT`` env vars are the
        canonical Nebius IAM credentials; recognising them keeps the MCP
        server interchangeable with the rest of the Nebius tooling.
        """
        explicit_token = (
            token
            or os.environ.get("CONTREE_TOKEN")
            or os.environ.get("NEBIUS_API_KEY")
        )
        explicit_project = (
            project
            or os.environ.get("CONTREE_PROJECT")
            or os.environ.get("NEBIUS_AI_PROJECT")
        )
        explicit_url = url or os.environ.get("CONTREE_URL")

        if explicit_token is not None:
            # Rule 1: file ignored. ``auth_type`` is the value the caller
            # passed in (server.amain forwards ``parser.auth_type``;
            # defaults to IAM). The default URL follows the auth scheme.
            base_url = self.DEFAULT_IAM_URL if auth_type == AuthType.IAM else ""
            return ConfigProfile(
                name="env",
                token=explicit_token,
                url=(explicit_url or base_url).rstrip("/"),
                auth_type=auth_type,
                project=explicit_project,
            )

        # Rule 2: file is consulted. The profile's ``type`` line is
        # authoritative — the caller-provided ``auth_type`` is ignored
        # here, because the stored token was issued for whichever scheme
        # the profile records.
        name = profile or os.environ.get("CONTREE_PROFILE") or self.__active
        stored = self.__profiles.get(name)

        if stored is not None:
            return ConfigProfile(
                name=name,
                token=stored.token,
                url=(explicit_url or stored.url).rstrip("/"),
                auth_type=stored.auth_type,
                project=explicit_project or stored.project,
            )

        # Unknown profile + no external token: return an empty stub.
        # The server's "No API token configured" check will catch this
        # and produce a helpful error.
        return ConfigProfile(
            name=name,
            token=None,
            url=(explicit_url or "").rstrip("/"),
            auth_type=AuthType.JWT,
            project=explicit_project,
        )
