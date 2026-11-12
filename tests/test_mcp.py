import pytest
from fastmcp import Client

from alz_compass.app import create_server
from alz_compass.config import Settings


@pytest.mark.asyncio
async def test_real_mcp_discovery_and_public_development_snapshot():
    async with Client(
        create_server(settings=Settings(alz_compass_data_mode="snapshot"))
    ) as client:
        tools = await client.list_tools()
        assert {t.name for t in tools} == {
            "find_completed_trials",
            "get_trial_evidence_card",
        }
        search_tool = next(t for t in tools if t.name == "find_completed_trials")
        assert "Type 2 Diabetes" in search_tool.description
        assert set(search_tool.input_schema["properties"]) == {"intervention", "limit"}
        search = (
            await client.call_tool("find_completed_trials", {"limit": 1})
        ).structured_content
        assert search["status"] == "ok"
        assert search["source_mode"] == "snapshot"
        assert search["criteria"]["condition"] == "Type 2 Diabetes"
        assert search["criteria"]["condition_label_filter"] == (
            "explicit_type2_diabetes_labels"
        )
        study = search["studies"][0]
        assert study["overall_status"] == "COMPLETED"
        assert study["study_type"] == "INTERVENTIONAL"
        card = (
            await client.call_tool(
                "get_trial_evidence_card", {"nct_id": study["nct_id"]}
            )
        ).structured_content
        assert card["status"] == "ok"
        assert card["card"]["identity"]["nct_id"] == study["nct_id"]
        assert card["card"]["source_mode"] == "snapshot"
        assert card["card"]["provenance"]["snapshot_sha256"]
        flags = {flag["code"] for flag in card["card"]["review_flags"]}
        assert "TYPE2_DIABETES_SCOPE_UNCONFIRMED" not in flags
        assert "DISEASE_RELEVANCE_REQUIRES_REVIEW" in flags


@pytest.mark.asyncio
@pytest.mark.parametrize("args", [{"limit": 6}, {"limit": True}, {"limit": 0}])
async def test_tool_input_schema_enforces_limit(args):
    async with Client(
        create_server(settings=Settings(alz_compass_data_mode="snapshot"))
    ) as client:
        result = await client.call_tool(
            "find_completed_trials", args, raise_on_error=False
        )
        assert result.is_error


@pytest.mark.asyncio
async def test_malformed_nct_rejected_by_mcp_schema():
    async with Client(
        create_server(settings=Settings(alz_compass_data_mode="snapshot"))
    ) as client:
        result = await client.call_tool(
            "get_trial_evidence_card",
            {"nct_id": "https://example.com"},
            raise_on_error=False,
        )
        assert result.is_error


@pytest.mark.asyncio
async def test_simulated_outage_is_explicit():
    async with Client(
        create_server(
            settings=Settings(
                alz_compass_data_mode="snapshot",
                alz_compass_test_fault="upstream_error",
            )
        )
    ) as client:
        result = (
            await client.call_tool("find_completed_trials", {})
        ).structured_content
        assert result["status"] == "upstream_error"
        assert result["search_incomplete"] is True


def test_live_mode_rejects_test_fault():
    with pytest.raises(ValueError, match="snapshot"):
        create_server(
            settings=Settings(
                alz_compass_data_mode="live", alz_compass_test_fault="upstream_error"
            )
        )
