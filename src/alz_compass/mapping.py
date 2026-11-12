"""Deterministic, source-preserving ClinicalTrials.gov API v2 evidence cards.

Source text is data: this module never executes, summarizes, or interprets it.
Output paths in provenance use JSONPath notation, including array indices.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any

from .disease import (
    POPULATION_REVIEW_MESSAGE,
    SCOPE_FLAG_CODE,
    SCOPE_UNCONFIRMED_MESSAGE,
    has_disease_label,
)

SCHEMA_VERSION = "1.0"
LABEL = "Registry extraction pending human review"
MISSING_DISPLAY = "Not reported in this record."
LIMITATIONS = [
    "Completed does not mean successful treatment or available results.",
    "No results posted in this registry does not mean no findings "
    "or publications exist.",
    "Eligibility criteria do not describe the actual enrolled population.",
    "Enrollment is not the number analyzed for a particular outcome.",
    "Registry-listed outcomes are not proof of prospective specification.",
    "Randomization and masking fields do not establish low risk of bias.",
    "Registry extraction does not establish treatment effectiveness "
    "or support treatment ranking.",
]


def _at(value: Any, path: str) -> Any:
    """Read our internal simple JSON paths without evaluating expressions."""
    for token in re.findall(r"[^.\[\]]+", path.removeprefix("$.")):
        if isinstance(value, dict):
            value = value.get(token)
        elif isinstance(value, list) and token.isdigit() and int(token) < len(value):
            value = value[int(token)]
        else:
            return None
    return value


def build_evidence_card(
    study: dict,
    *,
    retrieved_at: str,
    source_mode: str = "live",
    snapshot_sha256: str | None = None,
) -> dict:
    """Map one registry record without making clinical or treatment inferences.

    Missing and invalid scalar values become null. Missing arrays become null;
    explicit empty arrays remain empty. Malformed array entries keep their index
    and receive null fields, so neighboring relationships never shift.
    """
    if not isinstance(study, dict):
        raise TypeError("study must be a ClinicalTrials.gov record object")
    if source_mode not in {"live", "snapshot"}:
        raise ValueError("source_mode must be live or snapshot")

    flags: list[dict] = []
    fields: dict[str, dict] = {}

    def flag(code: str, field: str, message: str) -> None:
        flags.append({"code": code, "field": field, "message": message})

    def read(source: str, output: str, kind: type, *, required: bool = True) -> Any:
        raw = _at(study, source)
        fields[output] = {"source_path": source, "source_value": deepcopy(raw)}
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            if required:
                flag("MISSING_FIELD", output, MISSING_DISPLAY)
            return None
        # bool is a subclass of int; registry boolean and count fields are strict.
        if type(raw) is not kind:
            flag(
                "INVALID_SOURCE_TYPE",
                output,
                f"Expected {kind.__name__}; source value retained in provenance.",
            )
            return None
        return deepcopy(raw)

    def strings(source: str, output: str, *, required: bool = True) -> list | None:
        raw = read(source, output, list, required=required)
        if raw is None:
            return None
        return [
            read(f"{source}[{i}]", f"{output}[{i}]", str, required=required)
            for i in range(len(raw))
        ]

    def records(
        source: str, output: str, spec: dict[str, str | tuple[str, type]]
    ) -> list | None:
        raw = read(source, output, list)
        if raw is None:
            return None
        if not raw:
            flag(
                "EMPTY_REQUESTED_ARRAY",
                output,
                "No entries are reported in this array.",
            )
        mapped = []
        for i, record in enumerate(raw):
            src, dst = f"{source}[{i}]", f"{output}[{i}]"
            if not isinstance(record, dict):
                flag(
                    "INVALID_SOURCE_TYPE",
                    dst,
                    "Expected object; array position preserved.",
                )
            item = {}
            for key, mapping in spec.items():
                source_key, kind = (
                    mapping if isinstance(mapping, tuple) else (mapping, str)
                )
                item[key] = (
                    strings(f"{src}.{source_key}", f"{dst}.{key}", required=False)
                    if kind is list
                    else read(f"{src}.{source_key}", f"{dst}.{key}", kind)
                )
            mapped.append(item)
        return mapped

    def derived(output: str, source: str, description: str) -> None:
        fields[output] = {
            "source_path": source,
            "source_value": deepcopy(_at(study, source)),
            "derivation": description,
        }

    p = "$.protocolSection"
    identification = f"{p}.identificationModule"
    status = f"{p}.statusModule"
    design = f"{p}.designModule"
    eligibility = f"{p}.eligibilityModule"
    arms = f"{p}.armsInterventionsModule"
    nct_id = read(f"{identification}.nctId", "$.identity.nct_id", str)
    valid_nct = (
        isinstance(nct_id, str) and re.fullmatch(r"NCT\d{8}", nct_id) is not None
    )
    if nct_id is not None and not valid_nct:
        flag(
            "INVALID_NCT_ID",
            "$.identity.nct_id",
            "Record identifier is not a canonical NCT ID; source links omitted.",
        )
    study_url = f"https://clinicaltrials.gov/study/{nct_id}" if valid_nct else None
    api_url = (
        f"https://clinicaltrials.gov/api/v2/studies/{nct_id}" if valid_nct else None
    )
    derived(
        "$.identity.study_url",
        f"{identification}.nctId",
        "Canonical study URL from validated NCT ID.",
    )

    card = {
        "schema_version": SCHEMA_VERSION,
        "label": LABEL,
        "source_mode": source_mode,
        "identity": {
            "nct_id": nct_id,
            "title": read(f"{identification}.briefTitle", "$.identity.title", str),
            "official_title": read(
                f"{identification}.officialTitle",
                "$.identity.official_title",
                str,
                required=False,
            ),
            "conditions": strings(
                f"{p}.conditionsModule.conditions", "$.identity.conditions"
            ),
            "study_url": study_url,
        },
        "status": {
            "study_type": read(f"{design}.studyType", "$.status.study_type", str),
            "overall_status": read(
                f"{status}.overallStatus", "$.status.overall_status", str
            ),
            "completion_date": read(
                f"{status}.completionDateStruct.date", "$.status.completion_date", str
            ),
            "completion_date_type": read(
                f"{status}.completionDateStruct.type",
                "$.status.completion_date_type",
                str,
            ),
        },
        "design": {
            "phases": strings(f"{design}.phases", "$.design.phases"),
            "allocation": read(
                f"{design}.designInfo.allocation", "$.design.allocation", str
            ),
            "intervention_model": read(
                f"{design}.designInfo.interventionModel",
                "$.design.intervention_model",
                str,
            ),
            "masking": read(
                f"{design}.designInfo.maskingInfo.masking", "$.design.masking", str
            ),
            "who_masked": strings(
                f"{design}.designInfo.maskingInfo.whoMasked",
                "$.design.who_masked",
                required=False,
            ),
        },
        "enrollment": {
            "count": read(f"{design}.enrollmentInfo.count", "$.enrollment.count", int),
            "type": read(f"{design}.enrollmentInfo.type", "$.enrollment.type", str),
        },
        "population": {
            "eligibility_criteria": read(
                f"{eligibility}.eligibilityCriteria",
                "$.population.eligibility_criteria",
                str,
            ),
            "healthy_volunteers": read(
                f"{eligibility}.healthyVolunteers",
                "$.population.healthy_volunteers",
                bool,
                required=False,
            ),
            "sex": read(f"{eligibility}.sex", "$.population.sex", str, required=False),
            "minimum_age": read(
                f"{eligibility}.minimumAge",
                "$.population.minimum_age",
                str,
                required=False,
            ),
            "maximum_age": read(
                f"{eligibility}.maximumAge",
                "$.population.maximum_age",
                str,
                required=False,
            ),
            "interpretation": (
                "Eligibility criteria only; not actual enrolled-participant "
                "characteristics."
            ),
        },
        "arms": records(
            f"{arms}.armGroups",
            "$.arms",
            {
                "label": "label",
                "type": "type",
                "description": "description",
                "intervention_names": ("interventionNames", list),
            },
        ),
        "interventions": records(
            f"{arms}.interventions",
            "$.interventions",
            {
                "name": "name",
                "type": "type",
                "description": "description",
                "arm_group_labels": ("armGroupLabels", list),
                "other_names": ("otherNames", list),
            },
        ),
        "primary_outcomes": records(
            f"{p}.outcomesModule.primaryOutcomes",
            "$.primary_outcomes",
            {
                "measure": "measure",
                "description": "description",
                "time_frame": "timeFrame",
            },
        ),
    }
    has_results = read("$.hasResults", "$.results.has_results", bool)
    card["results"] = {
        "has_results": has_results,
        "status": "posted"
        if has_results is True
        else "not_posted"
        if has_results is False
        else "unknown",
        "url": f"{study_url}?tab=results"
        if has_results is True and study_url
        else study_url,
    }
    derived(
        "$.results.status",
        "$.hasResults",
        "Strict boolean true -> posted; false -> not_posted; other -> unknown.",
    )
    derived(
        "$.results.url",
        f"{identification}.nctId",
        "Canonical study URL; results tab only when hasResults is true.",
    )
    updated = read(
        f"{status}.lastUpdatePostDateStruct.date",
        "$.provenance.registry_update_date",
        str,
    )
    card["provenance"] = {
        "retrieved_at": retrieved_at,
        "registry_update_date": updated,
        "source_url": study_url,
        "api_url": api_url,
        "snapshot_sha256": snapshot_sha256,
        "fields": fields,
    }

    if card["status"]["overall_status"] != "COMPLETED":
        flag(
            "OUTSIDE_COMPLETED_SCOPE",
            "$.status.overall_status",
            "This record is not confirmed as COMPLETED.",
        )
    if card["status"]["study_type"] != "INTERVENTIONAL":
        flag(
            "OUTSIDE_INTERVENTIONAL_SCOPE",
            "$.status.study_type",
            "This record is not confirmed as INTERVENTIONAL.",
        )
    conditions = card["identity"]["conditions"] or []
    if not has_disease_label(conditions):
        flag(
            SCOPE_FLAG_CODE,
            "$.identity.conditions",
            SCOPE_UNCONFIRMED_MESSAGE,
        )
    flag(
        "DISEASE_RELEVANCE_REQUIRES_REVIEW",
        "$.population.eligibility_criteria",
        POPULATION_REVIEW_MESSAGE,
    )
    if card["enrollment"]["type"] == "ESTIMATED":
        flag(
            "ESTIMATED_ENROLLMENT",
            "$.enrollment.count",
            "Registry enrollment is estimated, not an actual count.",
        )
    if card["status"]["completion_date_type"] == "ESTIMATED":
        flag(
            "ESTIMATED_COMPLETION_DATE",
            "$.status.completion_date",
            "Registry completion date is estimated.",
        )
    if has_results is False:
        flag(
            "RESULTS_NOT_POSTED",
            "$.results.has_results",
            "No results posted in this registry; findings or publications "
            "may exist elsewhere.",
        )
    elif has_results is None:
        flag(
            "RESULTS_AVAILABILITY_UNKNOWN",
            "$.results.has_results",
            "Results availability cannot be determined from this record.",
        )

    # Preserve source relationships verbatim and flag unresolved links, never
    # guess an association by list order or similarity of intervention names.
    arm_labels = {
        item["label"] for item in card["arms"] or [] if item["label"] is not None
    }
    for i, item in enumerate(card["interventions"] or []):
        for label in item["arm_group_labels"] or []:
            if label is not None and label not in arm_labels:
                flag(
                    "UNRESOLVED_ARM_REFERENCE",
                    f"$.interventions[{i}].arm_group_labels",
                    "An intervention references an arm label absent "
                    "from the reported arm list.",
                )
    for output, items in [
        ("$.arms", card["arms"]),
        ("$.interventions", card["interventions"]),
    ]:
        link = "intervention_names" if output == "$.arms" else "arm_group_labels"
        for i, item in enumerate(items or []):
            if not item[link]:
                flag(
                    "ARM_INTERVENTION_LINK_NOT_REPORTED",
                    f"{output}[{i}].{link}",
                    "No explicit association is reported here; "
                    "do not infer it by array order.",
                )

    card["review_flags"] = flags
    card["limitations"] = list(LIMITATIONS)
    return card
