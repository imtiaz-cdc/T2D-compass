"""The two domain tasks exposed by the MCP server."""

from __future__ import annotations

from typing import Any

from .disease import (
    CONDITION_FILTER_MESSAGE,
    CONDITION_MATCH_RULE,
    SEARCH_CONDITION,
    SNAPSHOT_SEARCH_MESSAGE,
    has_disease_label,
)
from .mapping import build_evidence_card
from .registry import NCT_PATTERN, RegistryError, utc_now, validate_nct

MAX_SEARCH_PAGES = 3
SEARCH_PAGE_SIZE = 20


def _at(study: Any, *parts: str) -> Any:
    for part in parts:
        if not isinstance(study, dict):
            return None
        study = study.get(part)
    return study


class TrialService:
    def __init__(self, registry):
        self.registry = registry

    def _error(self, error: RegistryError) -> dict:
        return {
            "status": error.code,
            "source_mode": self.registry.source_mode,
            "error": error.as_dict(),
        }

    async def get_trial_evidence_card(self, nct_id: str) -> dict:
        try:
            validate_nct(nct_id)
            study = await self.registry.get_study(nct_id)
            if _at(study, "protocolSection", "identificationModule", "nctId") != nct_id:
                raise RegistryError(
                    "upstream_error",
                    "Registry returned a record with an unexpected identifier.",
                )
            metadata = self.registry.metadata(nct_id)
            card = build_evidence_card(
                study,
                retrieved_at=metadata["retrieved_at"],
                source_mode=self.registry.source_mode,
                snapshot_sha256=metadata.get("snapshot_sha256"),
            )
            return {
                "status": "ok",
                "source_mode": self.registry.source_mode,
                "card": card,
            }
        except RegistryError as error:
            return self._error(error)

    async def find_completed_trials(
        self, intervention: str | None = None, limit: int = 3
    ) -> dict:
        try:
            if type(limit) is not int or not 1 <= limit <= 5:
                raise RegistryError(
                    "invalid_input", "Limit must be an integer between 1 and 5."
                )
            if intervention is not None:
                if type(intervention) is not str or len(intervention) > 120:
                    raise RegistryError(
                        "invalid_input",
                        "Intervention must be text of no more than 120 characters.",
                    )
                intervention = intervention.strip() or None
        except RegistryError as error:
            return self._error(error)

        params = {
            "query.cond": SEARCH_CONDITION,
            "filter.overallStatus": "COMPLETED",
            "filter.advanced": "AREA[StudyType]INTERVENTIONAL",
            "format": "json",
            "pageSize": SEARCH_PAGE_SIZE,
        }
        if intervention:
            params["query.intr"] = intervention
        result = {
            "status": "ok",
            "source_mode": self.registry.source_mode,
            "criteria": {
                "condition": SEARCH_CONDITION,
                "condition_label_filter": CONDITION_MATCH_RULE,
                "status": "COMPLETED",
                "study_type": "INTERVENTIONAL",
                "intervention": intervention,
                "limit": limit,
                "api_parameters": dict(params),
            },
            "coverage": "bounded_candidates",
            "search_semantics": "bounded_snapshot"
            if self.registry.source_mode == "snapshot"
            else "registry_query_and_condition_labels",
            "retrieved_at": utc_now(),
            "studies": [],
            "returned_count": 0,
            "pages_fetched": 0,
            "records_examined": 0,
            "excluded_condition_count": 0,
            "search_incomplete": False,
            "review_flags": [
                {
                    "code": "NOT_AN_EXHAUSTIVE_SEARCH",
                    "message": (
                        "These are candidate records for review, "
                        "not an exhaustive evidence search."
                    ),
                },
                {
                    "code": "CONSERVATIVE_CONDITION_FILTER",
                    "message": CONDITION_FILTER_MESSAGE,
                },
            ],
        }
        if self.registry.source_mode == "snapshot":
            result["review_flags"].append(
                {
                    "code": "SNAPSHOT_SEARCH",
                    "message": SNAPSHOT_SEARCH_MESSAGE,
                }
            )
        seen_ids: set[str] = set()
        seen_tokens: set[str] = set()
        dropped = 0
        next_token = None
        try:
            for page_index in range(MAX_SEARCH_PAGES):
                page = await self.registry.search(params)
                result["pages_fetched"] += 1
                studies = page.get("studies")
                if not isinstance(studies, list):
                    raise RegistryError(
                        "upstream_error",
                        "Registry search returned an unexpected response structure.",
                    )
                next_token = page.get("nextPageToken")
                if next_token is not None and (
                    not isinstance(next_token, str) or not next_token
                ):
                    raise RegistryError(
                        "upstream_error",
                        "Registry search returned an invalid continuation token.",
                    )
                # A server ignoring pageSize cannot evade the fixed retrieval budget.
                for study in studies[:SEARCH_PAGE_SIZE]:
                    result["records_examined"] += 1
                    p = (
                        study.get("protocolSection", {})
                        if isinstance(study, dict)
                        else {}
                    )
                    nct_id = _at(p, "identificationModule", "nctId")
                    if (
                        not isinstance(nct_id, str)
                        or not NCT_PATTERN.fullmatch(nct_id)
                        or _at(p, "statusModule", "overallStatus") != "COMPLETED"
                        or _at(p, "designModule", "studyType") != "INTERVENTIONAL"
                    ):
                        dropped += 1
                        continue
                    if nct_id in seen_ids:
                        continue
                    seen_ids.add(nct_id)
                    has_results = study.get("hasResults")
                    has_results = has_results if type(has_results) is bool else None
                    conditions = _at(p, "conditionsModule", "conditions")
                    conditions = (
                        conditions
                        if isinstance(conditions, list)
                        and all(isinstance(x, str) for x in conditions)
                        else None
                    )
                    if not has_disease_label(conditions):
                        result["excluded_condition_count"] += 1
                        continue
                    title = _at(p, "identificationModule", "briefTitle")
                    result["studies"].append(
                        {
                            "nct_id": nct_id,
                            "title": title if isinstance(title, str) else None,
                            "conditions": conditions,
                            "overall_status": "COMPLETED",
                            "study_type": "INTERVENTIONAL",
                            "has_results": has_results,
                            "results_status": "posted"
                            if has_results is True
                            else "not_posted"
                            if has_results is False
                            else "unknown",
                            "study_url": f"https://clinicaltrials.gov/study/{nct_id}",
                        }
                    )
                    if len(result["studies"]) == limit:
                        # Reaching the user limit is deliberately a bounded result.
                        result["search_incomplete"] = True
                        break
                if len(studies) > SEARCH_PAGE_SIZE:
                    result["search_incomplete"] = True
                if len(result["studies"]) == limit:
                    break
                if not next_token:
                    break
                if next_token in seen_tokens:
                    result["search_incomplete"] = True
                    result["review_flags"].append(
                        {
                            "code": "REPEATED_PAGE_TOKEN",
                            "message": (
                                "Search stopped after a repeated continuation token."
                            ),
                        }
                    )
                    break
                seen_tokens.add(next_token)
                params["pageToken"] = next_token
            else:
                result["search_incomplete"] = bool(next_token)
        except RegistryError as error:
            result["status"] = error.code
            result["error"] = error.as_dict()
            result["search_incomplete"] = True

        result["returned_count"] = len(result["studies"])
        if result["status"] == "ok" and not result["studies"]:
            result["status"] = "no_matches"
        if dropped:
            result["review_flags"].append(
                {
                    "code": "SOURCE_RECORDS_EXCLUDED",
                    "message": (
                        f"Excluded {dropped} records with invalid identifiers "
                        "or outside the completed interventional scope."
                    ),
                }
            )
        if result["excluded_condition_count"]:
            result["review_flags"].append(
                {
                    "code": "CONDITION_LABELS_EXCLUDED",
                    "message": (
                        f"Excluded {result['excluded_condition_count']} examined "
                        "candidate records without a supported affirmative type 2 "
                        "diabetes condition label. Review broad or ambiguous "
                        "records separately if needed."
                    ),
                }
            )
        if result["search_incomplete"]:
            result["review_flags"].append(
                {
                    "code": "SEARCH_INCOMPLETE",
                    "message": (
                        "Search stopped at a requested or retrieval limit, "
                        "or encountered an upstream problem. "
                        "Additional matching records may exist."
                    ),
                }
            )
        return result
