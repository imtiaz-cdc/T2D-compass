"""Source-pairing regressions; these do not score a model or clinical quality."""

import asyncio
from copy import deepcopy

import pytest
from test_agent import FakeMCP, FakeModel, tool_call

from alz_compass.agent import ToolCallingAgent
from alz_compass.answer_fidelity import MISSING, outcome_block, preserve_outcome_wording


def card(nct_id="NCT00000011", outcomes=None):
    return {
        "identity": {
            "nct_id": nct_id,
            "title": "Synthetic source-pairing regression",
            "study_url": f"https://clinicaltrials.gov/study/{nct_id}",
            "conditions": ["Type 2 Diabetes"],
        },
        "source_mode": "synthetic",
        "status": {"overall_status": "COMPLETED", "completion_date": "2026-01"},
        "primary_outcomes": outcomes
        if outcomes is not None
        else [
            {
                "measure": "Glucose response",
                "time_frame": "Zero minutes before and 15, 30, 60 minutes "
                "after consumption.",
            },
            {"measure": "Acceptability", "time_frame": "At 4 hours"},
        ],
        "results": {"has_results": False, "status": "not_posted"},
        "enrollment": {"count": 0, "type": "ACTUAL"},
        "population": {"minimum_age": "12 Years", "healthy_volunteers": False},
        "review_flags": [{"message": "Review the participant population manually."}],
        "limitations": ["Registry extraction is not clinical approval."],
    }


def event(source):
    return {
        "name": "get_trial_evidence_card",
        "arguments": {"nct_id": source["identity"]["nct_id"]},
        "result": {"is_error": False, "data": {"status": "ok", "card": source}},
    }


def blocks(source):
    return "\n\n".join(
        outcome_block(source["identity"]["nct_id"], i, outcome)
        for i, outcome in enumerate(source["primary_outcomes"], 1)
    )


def test_before_after_error_replaced_without_mutating_source():
    source = card()
    untouched = deepcopy(source)
    wrong = "Primary outcomes: glucose at 0, 15, 30, 60 minutes after consumption."
    output, check = preserve_outcome_wording(
        "Prepare an evidence card.", wrong, [event(source)]
    )
    assert check["status"] == "source_backed_fallback"
    assert check["checked_outcomes"] == 2
    assert source == untouched
    assert wrong not in output
    assert blocks(source) in output
    assert "Enrollment: 0 (ACTUAL)" in output
    assert "Results posted: false" in output
    assert "Minimum Age: 12 Years" in output
    assert "Review the participant population manually." in output
    assert "Registry extraction is not clinical approval." in output
    assert source["identity"]["study_url"] in output


def test_swapped_timeframes_are_not_accepted_as_unpaired_substrings():
    source = card()
    swapped = deepcopy(source)
    (
        swapped["primary_outcomes"][0]["time_frame"],
        swapped["primary_outcomes"][1]["time_frame"],
    ) = (
        swapped["primary_outcomes"][1]["time_frame"],
        swapped["primary_outcomes"][0]["time_frame"],
    )
    output, check = preserve_outcome_wording(
        "Compare outcomes", blocks(swapped), [event(source)]
    )
    assert check["status"] == "source_backed_fallback"
    assert not any(item["exact_block_present"] for item in check["checks"])
    assert blocks(source) in output


def test_study_identity_and_outcome_order_are_checked():
    first = card()
    second = card(
        "NCT00000012", [{"measure": "Glucose response", "time_frame": "Week 24"}]
    )
    draft = blocks(first) + "\n" + blocks(second).replace("NCT00000012", "NCT00000011")
    output, check = preserve_outcome_wording(
        "Compare these studies", draft, [event(first), event(second)]
    )
    assert check["status"] == "source_backed_fallback"
    assert check["checked_outcomes"] == 3
    assert blocks(first) in output and blocks(second) in output
    assert output.index(blocks(first)) < output.index(blocks(second))


@pytest.mark.parametrize(
    "value, expected", [(None, MISSING), ("", ""), (0, "0"), (False, "false")]
)
def test_missing_and_false_zero_empty_values_are_distinct(value, expected):
    source = card(outcomes=[{"measure": "Response", "time_frame": value}])
    output, check = preserve_outcome_wording(
        "Prepare an evidence card", "Response measured soon.", [event(source)]
    )
    assert check["status"] == "source_backed_fallback"
    assert f"Timeframe: {expected}\n" in output
    if value is None:
        assert "Timeframe: not posted" not in output


def test_omitted_outcome_triggers_source_view_including_missing_pair():
    source = card(
        outcomes=[
            {"measure": "Response", "time_frame": "Week 6"},
            {"measure": None, "time_frame": None},
        ]
    )
    draft = outcome_block("NCT00000011", 1, source["primary_outcomes"][0])
    output, check = preserve_outcome_wording("Primary outcomes", draft, [event(source)])
    assert check["status"] == "source_backed_fallback"
    assert blocks(source) in output


def test_exact_source_blocks_leave_model_answer_unchanged():
    source = card()
    draft = "Registry extraction pending human review.\n" + blocks(source)
    output, check = preserve_outcome_wording(
        "Prepare an evidence card", draft, [event(source)]
    )
    assert output == draft
    assert check["status"] == "exact_source_blocks_present"
    assert check["final_output_source"] == "model"


def test_results_only_answer_is_not_replaced():
    draft = (
        "No posted registry results; that does not establish absence of publications."
    )
    output, check = preserve_outcome_wording(
        "Are results posted?", draft, [event(card())]
    )
    assert output == draft and check["status"] == "not_applicable"


def test_extra_timepoint_appended_to_source_timeframe_is_not_exact():
    source = card(outcomes=[{"measure": "Response", "time_frame": "Week 12"}])
    draft = blocks(source) + " and Week 24"
    output, check = preserve_outcome_wording(
        "Prepare an evidence card", draft, [event(source)]
    )
    assert check["status"] == "source_backed_fallback"
    assert "Timeframe: Week 12\n" in output
    assert "and Week 24" not in output


def test_volunteered_outcomes_are_checked_for_other_questions():
    output, check = preserve_outcome_wording(
        "Are results posted?", "Primary outcomes at 15 minutes.", [event(card())]
    )
    assert check["status"] == "source_backed_fallback"
    assert blocks(card()) in output


def test_later_failed_lookup_cannot_silently_reuse_prior_card():
    failed = event(card())
    failed["result"]["data"] = {"status": "upstream_error"}
    draft = "The source is unavailable; no card could be verified."
    output, check = preserve_outcome_wording(
        "Prepare an evidence card", draft, [event(card()), failed]
    )
    assert output == draft and check["status"] == "not_applicable"


def test_missing_cards_do_not_overwrite_refusal_or_failure():
    draft = "Registry cards cannot determine the best treatment."
    output, check = preserve_outcome_wording(
        "Compare treatments and choose the best.", draft, []
    )
    assert output == draft and check["checked_outcomes"] == 0


def test_comparison_fallback_keeps_search_and_failed_lookup_context():
    search = {
        "name": "find_completed_trials",
        "result": {
            "data": {
                "status": "ok",
                "source_mode": "snapshot",
                "returned_count": 1,
                "search_incomplete": True,
                "review_flags": [{"message": "Candidate limit reached."}],
            }
        },
    }
    failed = {
        "name": "get_trial_evidence_card",
        "arguments": {"nct_id": "NCT00000012"},
        "result": {"data": {"status": "not_found"}},
    }
    output, check = preserve_outcome_wording(
        "Compare evidence cards",
        "Here are the studies.",
        [search, event(card()), failed],
    )
    assert check["status"] == "source_backed_fallback"
    assert "Search incomplete: true" in output
    assert "Candidate limit reached." in output
    assert "get_trial_evidence_card — not_found" in output
    assert "not an exhaustive evidence search" in output


def test_agent_preserves_raw_draft_and_uses_no_extra_model_or_tool_call():
    source = card()
    wrong = "Primary outcomes at 0, 15, 30, 60 minutes after consumption."
    model = FakeModel(
        [
            tool_call("get_trial_evidence_card", {"nct_id": "NCT00000011"}),
            {"role": "assistant", "content": wrong},
        ]
    )
    mcp = FakeMCP({"status": "ok", "card": source})
    trace = asyncio.run(ToolCallingAgent(model, mcp).run("Prepare an evidence card"))
    assert trace["status"] == "completed"
    assert trace["model_calls"][-1]["message"]["content"] == wrong
    assert wrong not in trace["final_output"]
    assert blocks(source) in trace["final_output"]
    assert trace["source_fidelity"]["status"] == "source_backed_fallback"
    assert trace["manual_review"] == "pending"
    assert len(model.requests) == 2 and len(mcp.calls) == 1
    assert trace["prompt_version"] == "t2d-compass-1.1"
