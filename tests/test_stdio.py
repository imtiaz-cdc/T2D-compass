from pathlib import Path

import pytest

from alz_compass.agent import make_mcp_client


@pytest.mark.asyncio
async def test_actual_agent_stdio_client_uses_selected_manifest(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("ALZ_COMPASS_DATA_MODE", "snapshot")
    monkeypatch.setenv(
        "ALZ_COMPASS_MANIFEST", str(root / "data/type2diabetes/manifest-agent.json")
    )
    # The agent must always start stdio, even when the parent prefers HTTP.
    monkeypatch.setenv("MCP_TRANSPORT", "streamable-http")
    async with make_mcp_client() as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {
            "find_completed_trials",
            "get_trial_evidence_card",
        }
        result = await client.call_tool(
            "get_trial_evidence_card", {"nct_id": "NCT05743387"}
        )
        card = result.structured_content["card"]
        assert card["source_mode"] == "snapshot"
        assert card["status"]["overall_status"] != "COMPLETED"
        assert any(f["code"] == "OUTSIDE_COMPLETED_SCOPE" for f in card["review_flags"])


@pytest.mark.asyncio
async def test_actual_stdio_fault_fixture_is_observable(monkeypatch):
    monkeypatch.setenv("ALZ_COMPASS_DATA_MODE", "live")
    async with make_mcp_client(injected_failure=True) as client:
        result = await client.call_tool(
            "get_trial_evidence_card", {"nct_id": "NCT03244800"}
        )
        assert result.structured_content["status"] == "upstream_error"
        assert result.structured_content["source_mode"] == "snapshot"
