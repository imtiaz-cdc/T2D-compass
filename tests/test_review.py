import json

import pytest

from alz_compass.review import CORE_PATHS, evaluate, field_value, prepare


def test_reference_forms_are_blank_and_never_overwrite(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            [
                {
                    "nct_id": "NCT00000001",
                    "split": "development",
                    "source_url": "https://clinicaltrials.gov/study/NCT00000001",
                    "sha256": "test-fixture",
                }
            ]
        )
    )
    output = tmp_path / "review.json"
    prepare(manifest, output)
    form = json.loads(output.read_text())
    assert len(form["records"][0]["fields"]) == len(CORE_PATHS)
    assert all(f["annotated"] is False for f in form["records"][0]["fields"])
    assert form["records"][0]["reviewed_by"] == []
    with pytest.raises(ValueError, match="already exists"):
        prepare(manifest, output)


def test_field_path_is_not_executable():
    with pytest.raises(ValueError):
        field_value({}, "__import__('os')")
    assert (
        field_value({"results": {"has_results": False}}, "results.has_results") is False
    )


@pytest.mark.asyncio
async def test_unreviewed_records_cannot_receive_accuracy_score(tmp_path):
    from pathlib import Path

    manifest = Path(__file__).resolve().parents[1] / "data/type2diabetes/manifest.json"
    reference = tmp_path / "reference.json"
    prepare(manifest, reference)
    report = await evaluate(manifest, reference)
    assert report["status"] == "pending_review"
    assert report["pending_cards"] == 6
    assert report["compared_cards"] == 0
    assert report["field_accuracy"] is None
    assert report["heldout_included"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("expected_results,passed", [(False, True), (0, False)])
async def test_approved_references_compare_types_and_whole_cards(
    tmp_path, monkeypatch, expected_results, passed
):
    # Synthetic manual reference: this tests scoring, not public-data accuracy.
    from alz_compass import review

    card = {
        "identity": {"nct_id": "NCT00000001", "title": "Synthetic", "conditions": []},
        "status": {
            "study_type": "INTERVENTIONAL",
            "overall_status": "COMPLETED",
            "completion_date": "2020-01",
            "completion_date_type": "ACTUAL",
        },
        "design": {},
        "enrollment": {},
        "population": {},
        "arms": [],
        "interventions": [],
        "primary_outcomes": [],
        "results": {"has_results": False},
        "provenance": {"snapshot_sha256": "fixture-hash"},
    }

    class FakeService:
        def __init__(self, registry):
            pass

        async def get_trial_evidence_card(self, nct_id):
            return {"status": "ok", "card": card}

    monkeypatch.setattr(review, "SnapshotRegistry", lambda *args, **kwargs: None)
    monkeypatch.setattr(review, "TrialService", FakeService)
    fields = [
        {
            "path": p,
            "expected": field_value(card, p),
            "annotated": True,
            "source_location": "synthetic fixture",
        }
        for p in CORE_PATHS
    ]
    fields[-1]["expected"] = expected_results
    reference = tmp_path / "reference.json"
    reference.write_text(
        json.dumps(
            {
                "records": [
                    {
                        "nct_id": "NCT00000001",
                        "split": "development",
                        "review_status": "approved",
                        "reviewed_by": ["A", "B"],
                        "snapshot_sha256": "fixture-hash",
                        "fields": fields,
                    }
                ]
            }
        )
    )
    report = await evaluate(tmp_path / "unused.json", reference)
    assert report["status"] == ("passed" if passed else "failed")
    assert report["compared_fields"] == 14
    assert report["correct_fields"] == (14 if passed else 13)
    assert report["passed_cards"] == int(passed)
