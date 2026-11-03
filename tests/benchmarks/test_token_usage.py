"""Token usage benchmarks for the context each tool loading mode puts in front of a client.

Measures what a client receives before any tool runs: the server instructions plus the
``tools/list`` payload (name, description, input and output schema of every registered
tool). Tokens come from a stdlib estimator of about four characters per token, so the
numbers compare modes, tiers and tools against each other rather than predict what a
specific model will bill.
"""

import asyncio
import json
from collections import defaultdict
from collections.abc import Callable
from typing import Any

import pytest

from kubeflow_mcp.common.constants import TOOL_TO_PHASE
from kubeflow_mcp.core.server import create_server

# platform-admin sees every tool, so each mode is measured against the full tool set.
CLIENTS = ["trainer", "optimizer", "hub"]
PERSONA = "platform-admin"
MODES = ["full", "progressive", "semantic"]
TIERS = ["full", "compact", "minimal"]


def estimate_tokens(text: str) -> int:
    """Estimate tokens as ceil(characters / 4)."""
    return (len(text) + 3) // 4


def _compact_json(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def _static_surface(mode: str, tier: str = "full") -> tuple[str, dict[str, str]]:
    """Return the server instructions and each tool's serialized tools/list entry."""
    mcp = create_server(clients=CLIENTS, persona=PERSONA, mode=mode, instruction_tier=tier)
    tools = asyncio.run(mcp.list_tools())
    entries = {
        tool.name: _compact_json(
            tool.to_mcp_tool().model_dump(mode="json", exclude_none=True, by_alias=True)
        )
        for tool in tools
    }
    return mcp.instructions or "", entries


@pytest.mark.parametrize("tier", TIERS)
@pytest.mark.parametrize("mode", MODES)
def test_static_surface_tokens(
    record_token_usage: Callable[..., None], mode: str, tier: str
) -> None:
    instructions, entries = _static_surface(mode, tier)
    tools_tokens = sum(estimate_tokens(entry) for entry in entries.values())
    instructions_tokens = estimate_tokens(instructions)

    assert entries, f"no tools registered in {mode} mode"
    record_token_usage(
        f"surface_{mode}_{tier}",
        tool_count=len(entries),
        instructions_tokens=instructions_tokens,
        tools_tokens=tools_tokens,
        total_tokens=instructions_tokens + tools_tokens,
    )


def test_dynamic_modes_shrink_tool_schemas() -> None:
    _, full = _static_surface("full")
    full_tokens = sum(estimate_tokens(entry) for entry in full.values())

    for mode in ("progressive", "semantic"):
        _, entries = _static_surface(mode)
        tokens = sum(estimate_tokens(entry) for entry in entries.values())
        assert tokens < full_tokens, (
            f"{mode} tool schemas ({tokens}) not below full ({full_tokens})"
        )


def test_full_mode_tokens_by_category(record_token_usage: Callable[..., None]) -> None:
    _, entries = _static_surface("full")
    by_category: dict[str, list[str]] = defaultdict(list)
    for name, entry in entries.items():
        by_category[TOOL_TO_PHASE.get(name, "other")].append(entry)

    for category, category_entries in sorted(by_category.items()):
        tools_tokens = sum(estimate_tokens(entry) for entry in category_entries)
        record_token_usage(
            f"full_mode_category_{category}",
            tool_count=len(category_entries),
            instructions_tokens=0,
            tools_tokens=tools_tokens,
            total_tokens=tools_tokens,
        )
