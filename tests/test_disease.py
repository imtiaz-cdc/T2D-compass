"""Conservative research-scope boundaries, not clinical diagnostic tests."""

import pytest

from alz_compass.disease import has_disease_label


@pytest.mark.parametrize(
    "label",
    [
        "Type 2 Diabetes",
        "Type2 Diabetes Mellitus",
        "Type-2 Diabetes Mellitus",
        "Type II Diabetes",
        "TypeII Diabetes Mellitus",
        "Type Ⅱ Diabetes",  # Unicode Roman numeral.
        "Diabetes Mellitus, Type 2",
        "Diabetes Mellitus (Type II)",
        "Diabetes, Type2",
        "T2DM",
        "T2D",
        "NIDDM",
        "Non-Insulin-Dependent Diabetes Mellitus",
        "Diabetes Mellitus, Noninsulin Dependent",
        "Type 2 Diabetes Prevention",
        "Type 1 and Type 2 Diabetes",
        "Type 2 Diabetes and Healthy Volunteers",
        "Type 2 Diabetes Without Complications",
        "No Type 1 Diabetes; Type 2 Diabetes",
    ],
)
def test_supported_explicit_labels_identify_candidate_relevance(label):
    assert has_disease_label([label])


@pytest.mark.parametrize(
    "label",
    [
        "Diabetes",
        "Diabetes Mellitus",
        "Type 1 Diabetes",
        "Diabetes Mellitus, Type I",
        "Gestational Diabetes",
        "Prediabetes",
        "Prediabetic State",
        "Obesity",
        "Alzheimer Disease",
        "Insulin Resistance",
        "MODY",
        "Type 20 Diabetes",
        "Type III Diabetes",
        "T2DMlike",
        "Without Type2 Diabetes",
        "Adults Without Type 2 Diabetes Mellitus",
        "No history of Type II Diabetes",
        "Non-Type 2 Diabetes",
        "Type 2 Diabetes Absent",
        "Type 2 Diabetes Not Present",
        "Without Type 2 Diabetes (T2DM)",
        "No T2DM or NIDDM",
        "Without Non-Insulin-Dependent Diabetes Mellitus",
    ],
)
def test_unconfirmed_or_negated_labels_do_not_establish_type2_scope(label):
    assert not has_disease_label([label])


@pytest.mark.parametrize("conditions", [None, "Type 2 Diabetes", {}, [], [None, 2]])
def test_missing_or_invalid_condition_shapes_are_unconfirmed(conditions):
    assert not has_disease_label(conditions)


def test_mixed_labels_stay_eligible_when_one_affirmative_type2_label_is_present():
    assert has_disease_label(["Type 1 Diabetes", "Type 2 Diabetes", "Obesity"])
    assert has_disease_label(["Without Type 2 Diabetes", "T2DM"])
