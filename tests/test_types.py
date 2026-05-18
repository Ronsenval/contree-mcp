"""Tests for contree_mcp.types module."""

import base64

from contree_mcp.backend_types import (
    ConsumedResources,
    FileResponse,
    Image,
    ImageRegistry,
    ImportImageMetadata,
    InstanceMetadata,
    InstanceResourcesLimits,
    InstanceResult,
    OperationKind,
    OperationResponse,
    OperationResult,
    OperationStatus,
    OperationSummary,
    ProcessExitState,
    Stream,
    WhoAmIResponse,
)


class TestOperationResponse:
    """Tests for OperationResponse model."""

    def test_instance_operation(self) -> None:
        """Test creating an instance operation response."""
        response = OperationResponse(
            uuid="op-1",
            kind=OperationKind.INSTANCE,
            status=OperationStatus.SUCCESS,
            metadata=InstanceMetadata(
                command="echo hello",
                image="img-1",
                result=InstanceResult(
                    state=ProcessExitState(exit_code=0, pid=1, timed_out=False),
                    stdout=Stream(value="hello world", encoding="ascii"),
                    stderr=Stream(value="", encoding="ascii"),
                    resources=ConsumedResources(elapsed_time=1.0),
                ),
            ),
            result=OperationResult(image="img-result", tag=None),
        )

        assert response.uuid == "op-1"
        assert response.kind == OperationKind.INSTANCE
        assert response.status == OperationStatus.SUCCESS
        assert isinstance(response.metadata, InstanceMetadata)
        assert response.metadata.result.stdout.text() == "hello world"
        assert response.result is not None
        assert response.result.image == "img-result"

    def test_image_import_operation(self) -> None:
        """Test creating an image import operation response."""
        response = OperationResponse(
            uuid="op-2",
            kind=OperationKind.IMAGE_IMPORT,
            status=OperationStatus.SUCCESS,
            metadata=ImportImageMetadata(
                registry=ImageRegistry(url="docker://test"),
                tag="python:3.11",
            ),
            result=OperationResult(image="img-imported", tag="python:3.11"),
        )

        assert response.uuid == "op-2"
        assert response.kind == OperationKind.IMAGE_IMPORT
        assert response.status == OperationStatus.SUCCESS
        assert isinstance(response.metadata, ImportImageMetadata)
        assert response.result is not None
        assert response.result.image == "img-imported"
        assert response.result.tag == "python:3.11"

    def test_failed_operation(self) -> None:
        """Test creating a failed operation response."""
        response = OperationResponse(
            uuid="op-3",
            kind=OperationKind.INSTANCE,
            status=OperationStatus.FAILED,
            error="Command timed out",
        )

        assert response.status == OperationStatus.FAILED
        assert response.error == "Command timed out"


class TestStream:
    """Tests for Stream model."""

    def test_ascii_text(self) -> None:
        """Test getting text from ASCII stream."""
        stream = Stream(value="hello", encoding="ascii")
        assert stream.text() == "hello"

    def test_base64_text(self) -> None:
        """Test getting text from base64 stream."""
        encoded = base64.b64encode(b"hello binary").decode()
        stream = Stream(value=encoded, encoding="base64")
        assert stream.text() == "hello binary"

    def test_truncated_flag(self) -> None:
        """Test truncated flag."""
        stream = Stream(value="partial", encoding="ascii", truncated=True)
        assert stream.truncated is True
        assert stream.text() == "partial"


class TestInstanceMetadataNewFields:
    """Verify the API-1.0.0 fields the MCP previously dropped silently."""

    def test_defaults_match_spec(self) -> None:
        meta = InstanceMetadata(command="echo", image="img-1")
        # cwd defaults to "" (= use the image's default working dir),
        # NOT "/root" as the pre-fix code did.
        assert meta.cwd == ""
        assert meta.preserve_env is False
        assert meta.uid == 0
        assert meta.gid == 0
        assert meta.resources_limits.max_layer_bytes == 12 * 1024**3

    def test_env_accepts_none_to_unset(self) -> None:
        """``env`` values may be ``None`` to remove preserved vars."""
        meta = InstanceMetadata(
            command="echo",
            image="img-1",
            env={"FOO": "bar", "REMOVED": None},
        )
        assert meta.env == {"FOO": "bar", "REMOVED": None}

    def test_resources_limits_override(self) -> None:
        limits = InstanceResourcesLimits(max_layer_bytes=2 * 1024**3)
        meta = InstanceMetadata(command="echo", image="img-1", resources_limits=limits)
        assert meta.resources_limits.max_layer_bytes == 2 * 1024**3

    def test_uid_gid_round_trip(self) -> None:
        meta = InstanceMetadata(command="echo", image="img-1", uid=1000, gid=1000)
        dumped = meta.model_dump()
        assert dumped["uid"] == 1000
        assert dumped["gid"] == 1000
        assert dumped["preserve_env"] is False


class TestOperationTelemetry:
    """OperationSummary / OperationResponse now carry telemetry fields."""

    def test_summary_parses_telemetry(self) -> None:
        summary = OperationSummary.model_validate(
            {
                "uuid": "op-1",
                "kind": "instance",
                "status": "SUCCESS",
                "created_at": "2026-01-01T00:00:00Z",
                "duration": 12.5,
                "image_size": 1024,
                "consumed_cpu": 3.7,
                "consumed_memory": 4096,
                "image_uuid": "src-1",
                "result_image_uuid": "res-1",
            }
        )
        assert summary.duration == 12.5
        assert summary.image_size == 1024
        assert summary.consumed_cpu == 3.7
        assert summary.consumed_memory == 4096
        assert summary.image_uuid == "src-1"
        assert summary.result_image_uuid == "res-1"

    def test_summary_nullable_fields_default_to_none(self) -> None:
        """Older backends that don't send telemetry must not break parsing."""
        summary = OperationSummary(uuid="op-2", kind=OperationKind.INSTANCE, status=OperationStatus.PENDING)
        assert summary.duration is None
        assert summary.image_size is None
        assert summary.consumed_cpu is None
        assert summary.consumed_memory is None
        assert summary.image_uuid is None
        assert summary.result_image_uuid is None

    def test_response_telemetry_round_trip(self) -> None:
        response = OperationResponse(
            uuid="op-3",
            kind=OperationKind.INSTANCE,
            status=OperationStatus.SUCCESS,
            duration=0.5,
            image_size=99,
            consumed_cpu=0.25,
            consumed_memory=128,
            image_uuid="src",
            result_image_uuid="dst",
        )
        dumped = response.model_dump()
        assert dumped["duration"] == 0.5
        assert dumped["image_size"] == 99
        assert dumped["consumed_cpu"] == 0.25
        assert dumped["consumed_memory"] == 128
        assert dumped["image_uuid"] == "src"
        assert dumped["result_image_uuid"] == "dst"


class TestImageOperationUUID:
    def test_image_carries_operation_uuid(self) -> None:
        img = Image.model_validate(
            {
                "uuid": "img-1",
                "tag": "python:3.11",
                "created_at": "2026-01-01T00:00:00Z",
                "operation_uuid": "op-source",
            }
        )
        assert img.operation_uuid == "op-source"

    def test_image_operation_uuid_nullable(self) -> None:
        """Public/shared images legitimately omit the field."""
        img = Image(uuid="img-2", tag="alpine:3.20", created_at="2026-01-01T00:00:00Z")
        assert img.operation_uuid is None


class TestFileResponseExpanded:
    def test_post_response_only_required_fields(self) -> None:
        """POST /files returns uuid, sha256, size (no timestamps)."""
        resp = FileResponse(uuid="f-1", sha256="a" * 64, size=1024)
        assert resp.size == 1024
        assert resp.created_at is None
        assert resp.updated_at is None

    def test_get_response_with_timestamps(self) -> None:
        """GET /files/{sha256} carries full File schema."""
        resp = FileResponse.model_validate(
            {
                "uuid": "f-2",
                "sha256": "b" * 64,
                "size": 2048,
                "created_at": "2026-01-01T00:00:00Z",
                "updated_at": "2026-02-01T00:00:00Z",
            }
        )
        assert resp.created_at == "2026-01-01T00:00:00Z"
        assert resp.updated_at == "2026-02-01T00:00:00Z"


class TestWhoAmIResponse:
    def test_full_payload(self) -> None:
        resp = WhoAmIResponse.model_validate(
            {
                "token_uuid": "a1b2c3d4",
                "token_expiration": 1735689600,
                "permissions": {"import": True, "spawn": True, "cancel": False},
                "limits": {"instance_max_timeout": 3600, "instance_max_concurrency": 10},
                "operations_stat": {"completed": 42},
            }
        )
        assert resp.token_uuid == "a1b2c3d4"
        assert resp.token_expiration == 1735689600
        assert resp.permissions == {"import": True, "spawn": True, "cancel": False}
        assert resp.limits["instance_max_timeout"] == 3600
        assert resp.operations_stat == {"completed": 42}

    def test_nullable_expiration_and_empty_maps(self) -> None:
        resp = WhoAmIResponse(token_uuid="t-1")
        assert resp.token_expiration is None
        assert resp.permissions == {}
        assert resp.limits == {}
        assert resp.operations_stat == {}
