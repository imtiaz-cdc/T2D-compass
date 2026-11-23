"""Keep primary-outcome wording paired with its source, without model repair.

This is a bounded presentation check, not a factual or clinical judge. The raw
model draft remains in the agent trace even when a source-backed view is used.
"""

from __future__ import annotations

import re
from typing import Any

MISSING = "Not reported in this record."
OUTCOME_REQUEST = re.compile(
    r"\b(?:evidence\s+cards?|primary\s+outcomes?|registered\s+outcomes?|"
    r"time[ -]?frames?|compar(?:e|ison))\b",
    re.IGNORECASE,
)
OUTCOME_ANSWER = re.compile(
    r"\b(?:primary\s+outcomes?|time[ -]?frames?)\b", re.IGNORECASE
)


def _display(value: Any) -> str:
    if value is None:
        return MISSING
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return "; ".join(_display(item) for item in value) if value else "[]"
    return str(value)


def _at(card: dict, section: str, key: str) -> Any:
    value = card.get(section)
    return value.get(key) if isinstance(value, dict) else None


def _latest_cards(events: list[dict]) -> list[dict]:
    """A later failed lookup invalidates an earlier card for that identifier."""
    latest = {}
    for event in events:
        if event.get("name") != "get_trial_evidence_card":
            continue
        arguments = event.get("arguments", {})
        nct_id = arguments.get("nct_id") if isinstance(arguments, dict) else None
        if not isinstance(nct_id, str) or not re.fullmatch(r"NCT\d{8}", nct_id):
            continue
        latest[nct_id] = None
        result = event.get("result", {})
        if not isinstance(result, dict) or result.get("is_error"):
            continue
        data = result.get("data")
        if not isinstance(data, dict) or data.get("status") != "ok":
            continue
        card = data.get("card")
        if isinstance(card, dict) and _at(card, "identity", "nct_id") == nct_id:
            latest[nct_id] = card
    return [card for card in latest.values() if card is not None]


def outcome_block(nct_id: str, index: int, outcome: Any) -> str:
    """Canonical block keeps identity, position, measure and timeframe together."""
    outcome = outcome if isinstance(outcome, dict) else {}
    return (
        f"{nct_id} — Primary outcome {index}\n"
        f"Measure: {_display(outcome.get('measure'))}\n"
        f"Timeframe: {_display(outcome.get('time_frame'))}"
    )


def _source_view(cards: list[dict], events: list[dict]) -> str:
    lines = [
        "Registry extraction pending human review",
        "",
        "Source-backed evidence cards: primary outcomes and timeframes below "
        "retain the registry wording and pairing.",
        "Registry cards alone cannot establish treatment effectiveness, rank "
        "treatments or support a medical recommendation.",
    ]
    # Retain bounded-search and failure context when a comparison falls back.
    for event in events:
        result = event.get("result", {})
        data = result.get("data", {}) if isinstance(result, dict) else {}
        if not isinstance(data, dict):
            continue
        if event.get("name") == "find_completed_trials":
            lines.extend(
                [
                    "",
                    "Search context",
                    "Coverage: bounded candidates, not an exhaustive evidence search.",
                    f"Source mode: {_display(data.get('source_mode'))}",
                    f"Returned candidates: {_display(data.get('returned_count'))}",
                    f"Search incomplete: {_display(data.get('search_incomplete'))}",
                ]
            )
            for flag in data.get("review_flags", []):
                if isinstance(flag, dict) and flag.get("message"):
                    lines.append(f"- {flag['message']}")
        if data.get("status") not in {None, "ok"}:
            lines.append(
                f"Tool result: {event.get('name')} — {_display(data.get('status'))}. "
                "No study findings are inferred from this result."
            )
    for card in cards:
        nct_id = _at(card, "identity", "nct_id")
        lines.extend(
            [
                "",
                f"## {nct_id}: {_display(_at(card, 'identity', 'title'))}",
                f"Source: {_display(_at(card, 'identity', 'study_url'))}",
                f"Source mode: {_display(card.get('source_mode'))}",
                f"Retrieved: {_display(_at(card, 'provenance', 'retrieved_at'))}",
                "Registry update: "
                f"{_display(_at(card, 'provenance', 'registry_update_date'))}",
                f"Conditions: {_display(_at(card, 'identity', 'conditions'))}",
                f"Study type: {_display(_at(card, 'status', 'study_type'))}",
                f"Overall status: {_display(_at(card, 'status', 'overall_status'))}",
                f"Completion date: {_display(_at(card, 'status', 'completion_date'))} "
                f"({_display(_at(card, 'status', 'completion_date_type'))})",
                "",
                "### Design and enrollment",
            ]
        )
        for key in [
            "phases",
            "allocation",
            "intervention_model",
            "masking",
            "who_masked",
        ]:
            lines.append(
                f"{key.replace('_', ' ').title()}: {_display(_at(card, 'design', key))}"
            )
        lines.append(
            f"Enrollment: {_display(_at(card, 'enrollment', 'count'))} "
            f"({_display(_at(card, 'enrollment', 'type'))})"
        )
        for section, keys in [
            ("arms", ["label", "type", "description", "intervention_names"]),
            ("interventions", ["name", "type", "description", "arm_group_labels"]),
        ]:
            lines.extend(["", f"### {section.title()}"])
            entries = card.get(section)
            if not isinstance(entries, list) or not entries:
                lines.append(_display(entries))
                continue
            for index, entry in enumerate(entries, 1):
                entry = entry if isinstance(entry, dict) else {}
                lines.append(f"{section.title()} entry {index}")
                for key in keys:
                    lines.append(
                        f"- {key.replace('_', ' ').title()}: {_display(entry.get(key))}"
                    )
        lines.extend(["", "### Registry-listed primary outcomes"])
        outcomes = card.get("primary_outcomes")
        if isinstance(outcomes, list) and outcomes:
            for index, outcome in enumerate(outcomes, 1):
                lines.extend([outcome_block(nct_id, index, outcome), ""])
        else:
            lines.append(_display(outcomes))
        lines.extend(
            [
                "### Results availability",
                f"Results posted: {_display(_at(card, 'results', 'has_results'))}",
                f"Registry results status: {_display(_at(card, 'results', 'status'))}",
                f"Results/source URL: {_display(_at(card, 'results', 'url'))}",
                "Completion is separate from treatment success. No posted registry "
                "results does not establish that findings or publications are absent.",
                "",
                "### Population and interpretation",
                "Eligibility criteria are entry rules, not actual enrolled-participant "
                "characteristics. Enrollment is not the number analyzed "
                "for an outcome.",
            ]
        )
        for key in ["minimum_age", "maximum_age", "sex", "healthy_volunteers"]:
            lines.append(
                f"{key.replace('_', ' ').title()}: "
                f"{_display(_at(card, 'population', key))}"
            )
        lines.append(
            "Eligibility criteria: "
            f"{_display(_at(card, 'population', 'eligibility_criteria'))}"
        )
        lines.extend(["", "### Review flags and limitations"])
        for flag in card.get("review_flags", []):
            if isinstance(flag, dict) and flag.get("message"):
                lines.append(f"- {flag['message']}")
        for limit in card.get("limitations", []):
            lines.append(f"- {_display(limit)}")
        if card.get("source_mode") == "snapshot":
            lines.append(
                "Snapshot source; later registry changes have not been checked."
            )
        lines.append(
            "Registry-listed outcomes do not prove prospective specification. "
            "Design fields alone do not establish low risk of bias. "
            "No numerical outcome findings are extracted."
        )
    return "\n".join(lines)


def preserve_outcome_wording(
    question: str, draft: str, events: list[dict]
) -> tuple[str, dict]:
    """Accept exact source blocks or replace the draft with source-backed cards.

    Results-only answers remain unchanged unless they also present primary
    outcomes/timeframes. This does not semantically validate all model prose.
    """
    cards = _latest_cards(events)
    review = {
        "rule": "exact_primary_outcome_blocks_v1",
        "scope": "Primary outcome measures and timeframes; not clinical validation",
        "status": "not_applicable",
        "checked_outcomes": 0,
        "checks": [],
        "draft_preserved_at": "model_calls[-1].message.content",
        "final_output_source": "model",
    }
    if not (OUTCOME_REQUEST.search(question) or OUTCOME_ANSWER.search(draft)):
        return draft, review
    normalized = draft.replace("\r\n", "\n")
    for card in cards:
        outcomes = card.get("primary_outcomes")
        if not isinstance(outcomes, list):
            continue
        nct_id = _at(card, "identity", "nct_id")
        for index, outcome in enumerate(outcomes, 1):
            review["checks"].append(
                {
                    "nct_id": nct_id,
                    "outcome_index": index,
                    "exact_block_present": (
                        "\n" + outcome_block(nct_id, index, outcome) + "\n"
                    )
                    in ("\n" + normalized + "\n"),
                }
            )
    review["checked_outcomes"] = len(review["checks"])
    if not review["checks"]:
        return draft, review
    if all(check["exact_block_present"] for check in review["checks"]):
        review["status"] = "exact_source_blocks_present"
        return draft, review
    review.update(
        status="source_backed_fallback", final_output_source="registry_template"
    )
    return _source_view(cards, events), review
