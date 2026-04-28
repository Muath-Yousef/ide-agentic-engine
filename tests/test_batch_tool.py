"""Tests for the batch tool definition and BatchRequest serialisation."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from engine.mcp_gateway import (
    BATCH_TOOL_DEFINITION,
    BatchRequest,
    BatchResponse,
    ToolInvocation,
    ToolResult,
)


def test_batch_tool_definition_has_required_keys() -> None:
    assert "name" in BATCH_TOOL_DEFINITION
    assert "description" in BATCH_TOOL_DEFINITION
    assert "input_schema" in BATCH_TOOL_DEFINITION


def test_batch_tool_definition_is_json_serialisable() -> None:
    dumped = json.dumps(BATCH_TOOL_DEFINITION)
    reloaded = json.loads(dumped)
    assert reloaded["name"] == BATCH_TOOL_DEFINITION["name"]


def test_tool_invocation_requires_tool_name() -> None:
    with pytest.raises(ValidationError):
        ToolInvocation(arguments={})  # type: ignore[call-arg]


def test_tool_invocation_default_empty_arguments() -> None:
    inv = ToolInvocation(tool_name="echo")
    assert inv.arguments == {}


def test_batch_request_requires_at_least_one_invocation() -> None:
    with pytest.raises(ValidationError):
        BatchRequest(invocations=[])


def test_batch_request_serialisation_round_trip() -> None:
    original = BatchRequest(
        invocations=[
            ToolInvocation(tool_name="read_file", arguments={"path": "main.py"}),
            ToolInvocation(tool_name="run_command", arguments={"cmd": "pytest -q"}),
        ]
    )
    dumped = original.model_dump_json()
    restored = BatchRequest.model_validate_json(dumped)
    assert len(restored.invocations) == 2
    assert restored.invocations[0].tool_name == "read_file"


def test_tool_result_failure_fields() -> None:
    result = ToolResult(tool_name="broken", success=False, error="boom")
    assert result.success is False
    assert result.error == "boom"
    assert result.result is None


def test_batch_response_counts_match() -> None:
    response = BatchResponse(
        results=[
            ToolResult(tool_name="a", success=True, result="ok"),
            ToolResult(tool_name="b", success=False, error="fail"),
            ToolResult(tool_name="c", success=True, result="ok"),
        ],
        total=3,
        successful=2,
        failed=1,
        total_duration_ms=42.0,
        estimated_tokens_saved=3000,
    )
    assert response.successful + response.failed == response.total


def test_enum_tools_in_schema() -> None:
    """All declared tool names should appear in the schema enum."""
    declared_tools = {
        "read_file", "write_file", "apply_diff", "run_command",
        "search_web", "get_code_skeleton", "gdrive_read",
        "wazuh_query", "nuclei_scan",
    }
    schema_enum = set(
        BATCH_TOOL_DEFINITION["input_schema"]["properties"]["invocations"]
        ["items"]["properties"]["tool_name"]["enum"]
    )
    assert declared_tools == schema_enum
