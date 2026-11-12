"""Domain-tool cases; all records in this file are synthetic."""

from copy import deepcopy

import httpx
import pytest

from alz_compass.registry import RegistryClient, RegistryError
from alz_compass.service import TrialService


def study(
    nct_id="NCT00000001",
    *,
    status="COMPLETED",
    study_type="INTERVENTIONAL",
    has_results=False,
):
    return {
        "hasResults": has_results,
        "protocolSection": {
            "identificationModule": {
                "nctId": nct_id,
                "briefTitle": "Synthetic study only",
            },
            "statusModule": {"overallStatus": status},
            "designModule": {"studyType": study_type},
            "conditionsModule": {"conditions": ["Type 2 Diabetes"]},
        },
    }


class FakeRegistry:
    source_mode = "snapshot"

    def __init__(self, pages=None, record=None, failure=None):
        self.pages = pages or [{"studies": []}]
        self.record = record if record is not None else study()
        self.failure = failure
        self.calls = []

    def metadata(self, nct_id):
        return {
            "retrieved_at": "2026-01-01T00:00:00Z",
            "source_mode": "snapshot",
            "snapshot_sha256": "synthetic-test-fixture",
        }

    async def get_study(self, nct_id):
        self.calls.append(nct_id)
        if self.failure:
            raise self.failure
        return deepcopy(self.record)

    async def search(self, params):
        self.calls.append(dict(params))
        page = self.pages[len(self.calls) - 1]
        if isinstance(page, Exception):
            raise page
        return deepcopy(page)


async def test_search_enforces_filters_deduplicates_and_preserves_unknown_results():
    registry = FakeRegistry(
        pages=[
            {
                "studies": [
                    study("NCT00000001"),
                    study("NCT00000001"),
                    study("NCT00000002", status="RECRUITING"),
                    study("NCT00000003", study_type="OBSERVATIONAL"),
                    study("unsafe-id"),
                    study("NCT00000004", has_results=None),
                ]
            }
        ]
    )
    result = await TrialService(registry).find_completed_trials(limit=3)
    assert result["status"] == "ok"
    assert [item["nct_id"] for item in result["studies"]] == [
        "NCT00000001",
        "NCT00000004",
    ]
    assert result["studies"][0]["has_results"] is False
    assert result["studies"][1]["results_status"] == "unknown"
    assert result["returned_count"] == 2
    assert result["coverage"] == "bounded_candidates"
    assert result["search_semantics"] == "bounded_snapshot"
    assert result["search_incomplete"] is False
    assert registry.calls[0]["filter.advanced"] == "AREA[StudyType]INTERVENTIONAL"
    assert registry.calls[0]["filter.overallStatus"] == "COMPLETED"
    assert registry.calls[0]["query.cond"] == "Type 2 Diabetes"
    assert result["excluded_condition_count"] == 0
    assert any(f["code"] == "SOURCE_RECORDS_EXCLUDED" for f in result["review_flags"])


async def test_live_type2_query_skips_broad_matches_and_fetches_later_valid_labels():
    excluded = []
    for index, condition in enumerate(
        [
            "Obesity",
            "Diabetes",
            "Type 1 Diabetes",
            "Prediabetes",
            "Without Type 2 Diabetes (T2DM)",
        ],
        start=2,
    ):
        source = study(f"NCT{index:08}")
        source["protocolSection"]["conditionsModule"]["conditions"] = [condition]
        source["protocolSection"]["identificationModule"]["briefTitle"] = (
            "Synthetic obesity trial without Type 2 Diabetes"
        )
        excluded.append(source)
    calls = []

    def handler(request):
        calls.append(request)
        assert request.url.params["query.cond"] == "Type 2 Diabetes"
        assert request.url.params["filter.overallStatus"] == "COMPLETED"
        assert request.url.params["filter.advanced"] == "AREA[StudyType]INTERVENTIONAL"
        if len(calls) == 1:
            return httpx.Response(
                200, json={"studies": excluded, "nextPageToken": "next"}
            )
        assert request.url.params["pageToken"] == "next"
        return httpx.Response(200, json={"studies": [study()]})

    async with RegistryClient(transport=httpx.MockTransport(handler)) as registry:
        result = await TrialService(registry).find_completed_trials(limit=3)
    assert result["source_mode"] == "live"
    assert result["criteria"]["condition"] == "Type 2 Diabetes"
    assert result["criteria"]["condition_label_filter"] == (
        "explicit_type2_diabetes_labels"
    )
    assert result["search_semantics"] == "registry_query_and_condition_labels"
    assert [item["nct_id"] for item in result["studies"]] == ["NCT00000001"]
    assert result["studies"][0]["conditions"] == ["Type 2 Diabetes"]
    assert result["excluded_condition_count"] == 5
    assert result["records_examined"] == 6
    assert result["pages_fetched"] == 2
    assert result["search_incomplete"] is False
    assert {"CONSERVATIVE_CONDITION_FILTER", "CONDITION_LABELS_EXCLUDED"} <= {
        flag["code"] for flag in result["review_flags"]
    }
    assert result["coverage"] == "bounded_candidates"


async def test_direct_obesity_lookup_is_preserved_with_type2_scope_warning():
    source = study()
    source["protocolSection"]["conditionsModule"]["conditions"] = ["Obesity"]
    result = await TrialService(FakeRegistry(record=source)).get_trial_evidence_card(
        "NCT00000001"
    )
    assert result["status"] == "ok"
    assert result["card"]["identity"]["conditions"] == ["Obesity"]
    assert "TYPE2_DIABETES_SCOPE_UNCONFIRMED" in {
        flag["code"] for flag in result["card"]["review_flags"]
    }


async def test_search_limit_and_intervention_are_recorded():
    registry = FakeRegistry(
        pages=[
            {
                "studies": [study(f"NCT{i:08}") for i in range(1, 8)],
                "nextPageToken": "next",
            }
        ]
    )
    result = await TrialService(registry).find_completed_trials("  exercise  ", limit=5)
    assert result["returned_count"] == 5
    assert result["search_incomplete"] is True
    assert result["criteria"]["intervention"] == "exercise"
    assert registry.calls[0]["query.intr"] == "exercise"
    assert result["pages_fetched"] == 1


@pytest.mark.parametrize("limit", [0, 6, True, False, "3", 3.0, None])
async def test_invalid_limit_never_calls_registry(limit):
    registry = FakeRegistry()
    result = await TrialService(registry).find_completed_trials(limit=limit)
    assert result["status"] == "invalid_input"
    assert registry.calls == []


@pytest.mark.parametrize("intervention", [False, 42, [], "x" * 121])
async def test_invalid_intervention_never_calls_registry(intervention):
    registry = FakeRegistry()
    result = await TrialService(registry).find_completed_trials(intervention)
    assert result["status"] == "invalid_input"
    assert registry.calls == []


async def test_maximum_intervention_length_is_accepted():
    registry = FakeRegistry()
    result = await TrialService(registry).find_completed_trials("x" * 120)
    assert result["status"] == "no_matches"
    assert registry.calls[0]["query.intr"] == "x" * 120


async def test_three_page_budget_and_continuation():
    registry = FakeRegistry(
        pages=[
            {
                "studies": [study("NCT00000001", status="RECRUITING")],
                "nextPageToken": "one",
            },
            {"studies": [study("NCT00000002")], "nextPageToken": "two"},
            {"studies": [study("NCT00000003")], "nextPageToken": "three"},
        ]
    )
    result = await TrialService(registry).find_completed_trials()
    assert result["pages_fetched"] == 3
    assert result["returned_count"] == 2
    assert result["search_incomplete"] is True
    assert registry.calls[1]["pageToken"] == "one"
    assert registry.calls[2]["pageToken"] == "two"


async def test_repeated_page_token_stops_early():
    registry = FakeRegistry(pages=[{"studies": [], "nextPageToken": "same"}] * 3)
    result = await TrialService(registry).find_completed_trials()
    assert result["pages_fetched"] == 2
    assert result["search_incomplete"] is True
    assert any(f["code"] == "REPEATED_PAGE_TOKEN" for f in result["review_flags"])


async def test_partial_results_survive_upstream_failure_without_success_label():
    registry = FakeRegistry(
        pages=[
            {"studies": [study()], "nextPageToken": "next"},
            RegistryError("upstream_error", "Unavailable", True),
        ]
    )
    result = await TrialService(registry).find_completed_trials()
    assert result["status"] == "upstream_error"
    assert result["returned_count"] == 1
    assert result["search_incomplete"] is True
    assert result["error"]["retryable"] is True


async def test_empty_search_has_distinct_no_matches_status():
    result = await TrialService(FakeRegistry()).find_completed_trials()
    assert result["status"] == "no_matches"
    assert result["returned_count"] == 0
    assert result["search_incomplete"] is False


@pytest.mark.parametrize(
    "page", [{}, {"studies": {}}, {"studies": [], "nextPageToken": 7}]
)
async def test_malformed_search_payload_has_clear_failure(page):
    result = await TrialService(FakeRegistry(pages=[page])).find_completed_trials()
    assert result["status"] == "upstream_error"
    assert result["search_incomplete"] is True


async def test_get_card_uses_snapshot_metadata_and_keeps_scope_flags():
    registry = FakeRegistry(record=study(status="RECRUITING"))
    result = await TrialService(registry).get_trial_evidence_card("NCT00000001")
    assert result["status"] == "ok"
    assert result["card"]["provenance"]["retrieved_at"] == "2026-01-01T00:00:00Z"
    assert result["card"]["provenance"]["snapshot_sha256"] == "synthetic-test-fixture"
    assert result["card"]["source_mode"] == "snapshot"
    assert any(
        f["code"] == "OUTSIDE_COMPLETED_SCOPE" for f in result["card"]["review_flags"]
    )


async def test_invalid_get_id_never_calls_registry():
    registry = FakeRegistry()
    result = await TrialService(registry).get_trial_evidence_card("invalid")
    assert result["status"] == "invalid_input"
    assert registry.calls == []


async def test_mismatched_record_is_rejected_before_mapping():
    result = await TrialService(
        FakeRegistry(record=study("NCT00000002"))
    ).get_trial_evidence_card("NCT00000001")
    assert result["status"] == "upstream_error"
    assert "card" not in result


@pytest.mark.parametrize("code", ["not_found", "upstream_error"])
async def test_get_failure_status_is_preserved(code):
    registry = FakeRegistry(
        failure=RegistryError(code, "Safe failure", code == "upstream_error")
    )
    result = await TrialService(registry).get_trial_evidence_card("NCT00000001")
    assert result["status"] == code
    assert result["error"]["code"] == code
    assert "card" not in result
