"""Freeze a separate public type 2 diabetes set; never overwrite a prior capture.

Run from the repository root with its Python environment. No credentials needed.
Held-out records are downloaded and checked mechanically, never used to select
development examples or populate expected answers.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from alz_compass.disease import SEARCH_CONDITION, has_disease_label

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/type2diabetes"
EVAL = ROOT / "eval/type2diabetes"
BASE = "https://clinicaltrials.gov/api/v2"
CORE_PATHS = [
    "identity.nct_id",
    "identity.title",
    "identity.conditions",
    "status.study_type",
    "status.overall_status",
    "status.completion_date",
    "status.completion_date_type",
    "design",
    "enrollment",
    "population",
    "arms",
    "interventions",
    "primary_outcomes",
    "results.has_results",
]


def now():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def fetch(url):
    request = Request(url, headers={"User-Agent": "T2DCompassPublicData/0.4.0"})
    with urlopen(request, timeout=45) as response:
        if response.url.split("/api/")[0] != "https://clinicaltrials.gov":
            raise ValueError("Unexpected source origin")
        raw = response.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Unexpected source size")
    time.sleep(0.25)
    return raw, json.loads(raw), now()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def disease_label(study):
    conditions = (
        study.get("protocolSection", {})
        .get("conditionsModule", {})
        .get("conditions", [])
    )
    return has_disease_label(conditions)


def source_complete(study):
    """Require readable source fields, without deriving clinical judgments."""
    p = study.get("protocolSection", {})
    return bool(
        p.get("identificationModule", {}).get("briefTitle")
        and p.get("descriptionModule", {}).get("briefSummary")
        and p.get("eligibilityModule", {}).get("eligibilityCriteria")
        and any(
            outcome.get("measure")
            for outcome in p.get("outcomesModule", {}).get("primaryOutcomes", [])
        )
        and any(
            intervention.get("name")
            for intervention in p.get("armsInterventionsModule", {}).get(
                "interventions", []
            )
        )
    )


def main():
    if SEARCH_CONDITION != "Type 2 Diabetes":
        raise SystemExit("Collector requires the fixed type 2 diabetes profile.")
    if (DATA / "manifest.json").exists() or (EVAL / "bindings.example.json").exists():
        raise SystemExit(
            "A capture already exists. Preserve it; choose a new capture path "
            "for new data."
        )
    _, version, version_at = fetch(BASE + "/version")
    selection = {
        "created_at": version_at,
        "api_version": version,
        "condition_query": "Type 2 Diabetes",
        "method": (
            "Convenience starter set, not representative. For each development "
            "stratum in listed order, select the first unique result among the "
            "first 20 API relevance-ordered matches with an explicit type 2 "
            "diabetes condition label accepted by the app's shared matcher, "
            "TREATMENT primary purpose and nonempty title, brief summary, "
            "eligibility, primary outcome measure and intervention name. "
            "Strata: DRUG, BEHAVIORAL, PROCEDURE, each with posted=true then "
            "false. Held-out IDs are the first four unseen IDs from a separate "
            "completed/interventional condition query sorted by first posting "
            "date ascending and requesting only NCTId. Exclude every "
            "development-query candidate and known earlier dataset/candidate "
            "ID, not just selected development records. No held-out outcomes "
            "influence selection, examples or prompts. Exclusion is first "
            "eligible unused ACTIVE_NOT_RECRUITING interventional record with "
            "an explicit type 2 diabetes label."
        ),
        "scope_note": (
            "Condition labels and query matches are candidate relevance, not "
            "proof of participant diagnosis or a treatment-effect claim."
        ),
        "queries": [],
    }
    chosen = set()
    observed_ids = {
        "NCT05024032",
        "NCT01068743",
        "NCT03244800",
        "NCT00097500",
        "NCT01702311",
        "NCT05158244",
        "NCT02917031",
        "NCT01135394",
    }
    # Keep the original exposure exclusions portable without shipping old datasets.
    exposure = ROOT / "scripts/templates/prior-exposure-ids.json"
    observed_ids.update(json.loads(exposure.read_text("utf-8"))["nct_ids"])
    for manifest_path in (
        ROOT / "data/manifest.json",
        ROOT / "data/manifest-agent.json",
        ROOT / "data/obesity/manifest.json",
        ROOT / "data/obesity/manifest-agent.json",
    ):
        if manifest_path.exists():
            observed_ids.update(
                item["nct_id"]
                for item in json.loads(manifest_path.read_text("utf-8-sig"))
            )
    earlier_selection = ROOT / "data/obesity/selection.json"
    if earlier_selection.exists():
        for query in json.loads(earlier_selection.read_text())["queries"]:
            observed_ids.update(
                study["protocolSection"]["identificationModule"]["nctId"]
                for study in query["response"].get("studies", [])
            )
    entries = []
    dev_records = {}

    def search(label, status, advanced, fields, *, sort=None):
        params = {
            "query.cond": "Type 2 Diabetes",
            "filter.overallStatus": status,
            "filter.advanced": advanced,
            "pageSize": 20,
            "countTotal": "true",
            "fields": fields,
            "format": "json",
        }
        if sort:
            params["sort"] = sort
        url = BASE + "/studies?" + urlencode(params)
        _, response, retrieved = fetch(url)
        selection["queries"].append(
            {
                "stratum": label,
                "parameters": params,
                "source_url": url,
                "retrieved_at": retrieved,
                "response": response,
            }
        )
        if fields != "NCTId":
            observed_ids.update(
                s["protocolSection"]["identificationModule"]["nctId"]
                for s in response["studies"]
            )
        return response["studies"]

    def freeze(nct_id, split, reason, *, exclusion=False):
        if not re.fullmatch(r"NCT\d{8}", nct_id) or nct_id in chosen:
            raise ValueError("Invalid or duplicate selection")
        url = BASE + "/studies/" + nct_id + "?format=json"
        raw, study, retrieved = fetch(url)
        protocol = study["protocolSection"]
        assert protocol["identificationModule"]["nctId"] == nct_id
        assert protocol["designModule"]["studyType"] == "INTERVENTIONAL"
        expected_status = "ACTIVE_NOT_RECRUITING" if exclusion else "COMPLETED"
        assert protocol["statusModule"]["overallStatus"] == expected_status
        # The reader validates every file against its declared public split.
        # Exclusions stay in development, with explicit non-benchmark metadata.
        relative = f"public/{split}/{nct_id}.json"
        path = DATA / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise ValueError("Refusing to replace saved public source")
        path.write_bytes(raw)
        entry = {
            "nct_id": nct_id,
            "split": split,
            "file": relative,
            "source_url": f"https://clinicaltrials.gov/study/{nct_id}",
            "api_url": url,
            "retrieved_at": retrieved,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "review_status": "pending_independent_review",
            "selection_reason": reason,
        }
        if exclusion:
            entry.update(purpose="exclusion", benchmark_member=False)
        chosen.add(nct_id)
        if split == "development":
            dev_records[nct_id] = study
        return entry

    fields = (
        "NCTId,BriefTitle,Condition,InterventionType,InterventionName,HasResults,"
        "BriefSummary,EligibilityCriteria,PrimaryOutcomeMeasure,DesignPrimaryPurpose"
    )
    for intervention_type in ("DRUG", "BEHAVIORAL", "PROCEDURE"):
        for posted in (True, False):
            label = f"{intervention_type.lower()}_results_{str(posted).lower()}"
            advanced = (
                "AREA[StudyType]INTERVENTIONAL AND "
                f"AREA[InterventionType]{intervention_type} AND "
                f"AREA[HasResults]{str(posted).lower()} AND "
                "AREA[DesignPrimaryPurpose]TREATMENT"
            )
            candidates = search(label, "COMPLETED", advanced, fields)
            candidate = next(
                (
                    s
                    for s in candidates
                    if disease_label(s)
                    and source_complete(s)
                    and s["protocolSection"]["identificationModule"]["nctId"]
                    not in chosen
                ),
                None,
            )
            if candidate is None:
                raise ValueError(f"No eligible unique record in stratum {label}")
            nct_id = candidate["protocolSection"]["identificationModule"]["nctId"]
            entry = freeze(nct_id, "development", label)
            study = dev_records[nct_id]
            assert study.get("hasResults") is posted
            assert disease_label(study) and source_complete(study)
            assert (
                study["protocolSection"]["designModule"]["designInfo"]["primaryPurpose"]
                == "TREATMENT"
            )
            assert any(
                i.get("type") == intervention_type
                for i in study["protocolSection"]["armsInterventionsModule"][
                    "interventions"
                ]
            )
            entries.append(entry)
            print(f"Development {label}: {nct_id}", flush=True)

    heldout_candidates = search(
        "heldout_id_only",
        "COMPLETED",
        "AREA[StudyType]INTERVENTIONAL",
        "NCTId",
        sort="StudyFirstPostDate:asc",
    )
    heldout_ids = [
        s["protocolSection"]["identificationModule"]["nctId"]
        for s in heldout_candidates
        if s["protocolSection"]["identificationModule"]["nctId"]
        not in (chosen | observed_ids)
    ][:4]
    if len(heldout_ids) != 4:
        raise ValueError("Insufficient held-out candidates")
    for nct_id in heldout_ids:
        entries.append(
            freeze(nct_id, "heldout", "first_unused_id_from_separate_condition_query")
        )
    print("Four held-out records frozen without displaying their content.", flush=True)

    candidates = search(
        "active_exclusion",
        "ACTIVE_NOT_RECRUITING",
        "AREA[StudyType]INTERVENTIONAL",
        fields,
    )
    candidate = next(
        s
        for s in candidates
        if disease_label(s)
        and s["protocolSection"]["identificationModule"]["nctId"] not in chosen
    )
    excluded_id = candidate["protocolSection"]["identificationModule"]["nctId"]
    exclusion = freeze(
        excluded_id, "development", "active_interventional_exclusion", exclusion=True
    )
    print(f"Active exclusion: {excluded_id}", flush=True)
    write_json(DATA / "manifest.json", entries)
    write_json(
        DATA / "manifest-agent.json",
        [e for e in entries if e["split"] == "development"] + [exclusion],
    )
    write_json(DATA / "selection.json", selection)
    write_json(
        DATA / "review/reference-annotations.json",
        {
            "schema_version": "1.0",
            "created_at": now(),
            "instructions": (
                "Annotate directly from the source before viewing generated "
                "cards. expected is a JSON value; set annotated=true even for "
                "an intentionally missing/null value. Each record requires two "
                "independent reviewers and agreement before "
                "review_status=approved. Do not derive gold answers from the "
                "mapper. Do not use held-out answers to tune implementation "
                "or prompts."
            ),
            "records": [
                {
                    "nct_id": e["nct_id"],
                    "split": e["split"],
                    "source_url": e["source_url"],
                    "snapshot_sha256": e["sha256"],
                    "review_status": "pending",
                    "reviewed_by": [],
                    "fields": [
                        {
                            "path": p,
                            "expected": None,
                            "annotated": False,
                            "source_location": "",
                            "note": "",
                        }
                        for p in CORE_PATHS
                    ],
                }
                for e in entries
            ],
        },
    )
    bindings = {
        "completed_trial": entries[0]["nct_id"],
        "without_results_trial": entries[1]["nct_id"],
        "second_trial": entries[2]["nct_id"],
        "outside_scope_trial": excluded_id,
        "intervention": next(
            i["name"]
            for i in dev_records[entries[0]["nct_id"]]["protocolSection"][
                "armsInterventionsModule"
            ]["interventions"]
            if i.get("type") == "DRUG" and "placebo" not in i["name"].casefold()
        ),
        "missing_trial": "NCT99999999",
    }
    write_json(EVAL / "bindings.example.json", bindings)
    source = (ROOT / "scripts/templates/agent-scenarios-original.json").read_text(
        encoding="utf-8"
    )
    for before, after in (
        ("ALZ Compass", "T2D Compass"),
        ("Alzheimer's-related", "type 2 diabetes-related"),
        ("Alzheimer's disease", "type 2 diabetes"),
        ("Alzheimer's", "type 2 diabetes"),
        ("ALZ_COMPASS_LITE_NO_MATCH_87C4", "T2D_COMPASS_NO_MATCH_87C4"),
    ):
        source = source.replace(before, after)
    source = source.replace("an type 2 diabetes", "a type 2 diabetes")
    suite = json.loads(source)
    suite["dataset_manifest"] = "data/type2diabetes/manifest-agent.json"
    suite["source_baseline"] = (
        "New type 2 diabetes suite; no Alzheimer or obesity run or score applies."
    )
    write_json(EVAL / "agent_scenarios.json", suite)

    # Hash checks read bytes; held-out expected facts are not produced or printed.
    for entry in entries + [exclusion]:
        assert (
            hashlib.sha256((DATA / entry["file"]).read_bytes()).hexdigest()
            == entry["sha256"]
        )
    assert len(entries) == 10 and len(chosen) == 11
    assert len([e for e in entries if e["split"] == "development"]) == 6
    assert len([e for e in entries if e["split"] == "heldout"]) == 4
    assert bindings["missing_trial"] not in chosen
    for scenario in suite["scenarios"]:
        scenario["prompt"].format(**bindings)
    write_json(
        EVAL / "results/fixture-validation.json",
        {
            "created_at": now(),
            "status": "passed",
            "verification_type": "public_source_capture_and_fixture_checks",
            "core_records": 10,
            "development_records": 6,
            "heldout_records": 4,
            "exclusion_records": 1,
            "all_snapshot_hashes_verified": True,
            "development_strata": [
                e["selection_reason"] for e in entries if e["split"] == "development"
            ],
            "all_development_records_completed_interventional": True,
            "active_exclusion_status": "ACTIVE_NOT_RECRUITING",
            "active_exclusion_id": excluded_id,
            "all_twelve_scenario_placeholders_resolved": len(suite["scenarios"]) == 12,
            "missing_identifier_absent_from_snapshot": True,
            "live_missing_identifier_check": (
                "not_performed; recheck before live evaluation"
            ),
            "heldout_content_used_for_tuning": False,
            "reference_answers": "blank_pending_independent_review",
            "model_evaluation": "not_run",
            "clinical_review": "pending",
            "disclosure": (
                "Mechanical capture and fixture suitability checks are not "
                "clinical validation, reviewed reference accuracy or "
                "model evaluation."
            ),
        },
    )
    print(
        json.dumps(
            {"bindings": bindings, "core_records": 10, "exclusion_records": 1}, indent=2
        )
    )


if __name__ == "__main__":
    main()
