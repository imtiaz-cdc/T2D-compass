"""Independent reference forms and exact comparison after human approval."""

import argparse
import asyncio
import json
import re
from pathlib import Path

from alz_compass.registry import SnapshotRegistry, utc_now
from alz_compass.service import TrialService

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


def field_value(card, path):
    if not isinstance(path, str) or not re.fullmatch(r"[a-z_]+(?:\.[a-z_]+)*", path):
        raise ValueError("Invalid reference field path")
    value = card
    for key in path.split("."):
        if not isinstance(value, dict) or key not in value:
            raise ValueError("Reference field does not exist in the card")
        value = value[key]
    return value


def prepare(manifest, output):
    entries = json.loads(manifest.read_text(encoding="utf-8-sig"))
    form = {
        "schema_version": "1.0",
        "created_at": utc_now(),
        "instructions": (
            "Annotate directly from the source before viewing generated cards. "
            "expected is a JSON value; set annotated=true even for an intentionally "
            "missing/null value. Each record requires independent review and "
            "agreement before review_status=approved. "
            "Do not derive gold answers from the mapper."
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
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise ValueError(
            "Review form already exists; choose a new path to preserve annotations"
        )
    output.write_text(json.dumps(form, indent=2), encoding="utf-8")


async def evaluate(manifest, reference, include_heldout=False):
    form = json.loads(reference.read_text(encoding="utf-8-sig"))
    registry = SnapshotRegistry(manifest, include_heldout=include_heldout)
    service = TrialService(registry)
    report = {
        "created_at": utc_now(),
        "type": "independent_reference_comparison",
        "heldout_included": include_heldout,
        "records": [],
        "compared_fields": 0,
        "correct_fields": 0,
        "passed_cards": 0,
        "compared_cards": 0,
        "pending_cards": 0,
        "critical_errors": [],
        "clinical_validation": "requires human interpretation review",
    }
    for reference_card in form["records"]:
        if reference_card["split"] == "heldout" and not include_heldout:
            continue
        result = {"nct_id": reference_card["nct_id"], "status": "pending_review"}
        report["records"].append(result)
        fields = reference_card.get("fields", [])
        valid_review = (
            reference_card.get("review_status") == "approved"
            and len(set(reference_card.get("reviewed_by", []))) >= 2
            and {f.get("path") for f in fields} == set(CORE_PATHS)
            and len(fields) == len(CORE_PATHS)
            and all(
                f.get("annotated") is True and f.get("source_location") for f in fields
            )
        )
        if not valid_review:
            report["pending_cards"] += 1
            continue
        actual = await service.get_trial_evidence_card(reference_card["nct_id"])
        if actual["status"] != "ok":
            result.update(status="failed", error=actual.get("error"))
            report["compared_cards"] += 1
            continue
        if (
            actual["card"]["provenance"]["snapshot_sha256"]
            != reference_card["snapshot_sha256"]
        ):
            result.update(status="snapshot_mismatch")
            report["pending_cards"] += 1
            continue
        checks = []
        for expected in fields:
            observed = field_value(actual["card"], expected["path"])
            # JSON serialization keeps false distinct from 0 in exact comparison.
            correct = json.dumps(observed, sort_keys=True) == json.dumps(
                expected["expected"], sort_keys=True
            )
            checks.append(
                {
                    "path": expected["path"],
                    "passed": correct,
                    "expected": expected["expected"],
                    "actual": observed,
                }
            )
            report["compared_fields"] += 1
            report["correct_fields"] += int(correct)
        passed = all(c["passed"] for c in checks)
        result.update(status="passed" if passed else "failed", checks=checks)
        report["compared_cards"] += 1
        report["passed_cards"] += int(passed)
    report["status"] = (
        "pending_review"
        if report["pending_cards"] or not report["compared_cards"]
        else "passed"
        if report["passed_cards"] == report["compared_cards"]
        else "failed"
    )
    report["field_accuracy"] = (
        report["correct_fields"] / report["compared_fields"]
        if report["compared_fields"]
        else None
    )
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "evaluate"])
    parser.add_argument(
        "--manifest", type=Path, default=Path("data/type2diabetes/manifest.json")
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=Path("data/type2diabetes/review/reference-annotations.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/type2diabetes/results/reference-evaluation.json"),
    )
    parser.add_argument("--include-heldout", action="store_true")
    args = parser.parse_args()
    if args.action == "prepare":
        prepare(args.manifest, args.reference)
        print(f"Blank independent review form: {args.reference}")
        return 0
    report = asyncio.run(evaluate(args.manifest, args.reference, args.include_heldout))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        f"Reference evaluation: {report['status']}; "
        f"{report['compared_cards']} reviewed cards compared"
    )
    return 0 if report["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
