"""Tests for the whoami tool / client method."""

import pytest

from contree_mcp.backend_types import WhoAmIResponse
from contree_mcp.tools.whoami import whoami
from tests.conftest import FakeResponse, FakeResponses

from . import TestCase


class TestWhoAmIHappyPath(TestCase):
    @pytest.fixture
    def fake_responses(self) -> FakeResponses:
        return {
            "GET /whoami": FakeResponse(
                body=WhoAmIResponse(
                    token_uuid="a1b2c3d4",
                    token_expiration=1735689600,
                    permissions={"import": True, "spawn": True, "cancel": False},
                    limits={"instance_max_timeout": 3600, "instance_max_concurrency": 10},
                    operations_stat={"completed": 0},
                ),
            ),
        }

    @pytest.mark.asyncio
    async def test_returns_full_payload(self) -> None:
        result = await whoami()
        assert isinstance(result, WhoAmIResponse)
        assert result.token_uuid == "a1b2c3d4"
        assert result.token_expiration == 1735689600
        assert result.permissions == {"import": True, "spawn": True, "cancel": False}
        assert result.limits["instance_max_timeout"] == 3600

    @pytest.mark.asyncio
    async def test_returns_typed_response(self) -> None:
        result = await whoami()
        assert isinstance(result, WhoAmIResponse)


class TestWhoAmINullableExpiration(TestCase):
    """Token without an expiry returns null — must not break parsing."""

    @pytest.fixture
    def fake_responses(self) -> FakeResponses:
        return {
            "GET /whoami": FakeResponse(
                body={
                    "token_uuid": "perpetual",
                    "token_expiration": None,
                    "permissions": {},
                    "limits": {},
                    "operations_stat": {},
                }
            ),
        }

    @pytest.mark.asyncio
    async def test_nullable_expiration(self) -> None:
        result = await whoami()
        assert result.token_expiration is None
        assert result.permissions == {}
