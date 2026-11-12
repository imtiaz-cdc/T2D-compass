"""Fixed type 2 diabetes scope shared by search and evidence-card review.

Label matching identifies candidate relevance only. It does not establish a
diagnosis or the characteristics of enrolled participants.
"""

import re
import unicodedata
from typing import Any

APP_NAME = "T2D Compass"
SEARCH_CONDITION = "Type 2 Diabetes"
PROMPT_VERSION = "t2d-compass-1.0"
DEFAULT_MANIFEST = "data/type2diabetes/manifest.json"
SCOPE_FLAG_CODE = "TYPE2_DIABETES_SCOPE_UNCONFIRMED"
CONDITION_MATCH_RULE = "explicit_type2_diabetes_labels"
CONDITION_FILTER_MESSAGE = (
    "Candidates must have an explicit supported type 2 diabetes condition label. "
    "This conservative screen may miss relevant studies labeled only as diabetes "
    "or described in other fields. A matching label is not a participant diagnosis."
)
SCOPE_UNCONFIRMED_MESSAGE = (
    "Type 2 diabetes relevance is not established by the condition labels; "
    "review source context. Generic diabetes, type 1 diabetes, gestational "
    "diabetes, prediabetes or obesity alone do not establish type 2 diabetes scope."
)
POPULATION_REVIEW_MESSAGE = (
    "Confirm type 2 diabetes relevance and eligibility/population context "
    "manually, including prevention studies and mixed populations. Condition "
    "labels and eligibility criteria do not establish enrolled participants' "
    "diagnoses, glucose control, complications or a treatment effect."
)
SNAPSHOT_SEARCH_MESSAGE = (
    "Search covers only the selected frozen public records. Conditions match "
    "explicit type 2 diabetes labels or the supported T2D, T2DM and NIDDM aliases; "
    "generic diabetes and other diabetes types alone are not sufficient. "
    "Intervention text uses literal matching, not the live registry search engine."
)

# Selected retrieval aliases, not a clinical equivalence or treatment rule.
# NLM MeSH D003924 lists Type II, NIDDM and non-insulin-dependent forms:
# https://meshb.nlm.nih.gov/record/ui?ui=D003924 (checked 2026-10-28).
# Do not expand to every MeSH entry term (which can be only closely related).
_TYPE = r"type\s*(?:2|ii)"
_DIABETES = r"diabetes(?:\s+mellitus)?"
_NON_INSULIN = r"non\s*insulin\s+dependent"
_LABEL_TERM = re.compile(
    rf"\b(?:{_TYPE}\s*{_DIABETES}|{_DIABETES}\s+{_TYPE}|"
    rf"t2d|t2dm|niddm|{_NON_INSULIN}\s+{_DIABETES}|"
    rf"{_DIABETES}\s+{_NON_INSULIN})\b"
)
_NEGATED_PREFIX = re.compile(
    r"\b(?:no|not|without|non|absence\s+of|free\s+of)"
    r"(?:\s+(?:known|current|history|evidence|diagnosis|of|diagnosed|with|"
    r"existing|established|preexisting|prior))*\s*$"
)
_NEGATED_SUFFIX = re.compile(r"^\s+(?:absent|excluded|not\s+present)\b")


def _matches_label(label: str) -> bool:
    # Normalize only for matching; the mapper retains the original source text.
    normalized = re.sub(
        r"[^\w;.!?\n]+|_", " ", unicodedata.normalize("NFKC", label).casefold()
    )
    previous_negated_end = None
    for match in _LABEL_TERM.finditer(normalized):
        negated = bool(
            _NEGATED_PREFIX.search(normalized[: match.start()])
            or _NEGATED_SUFFIX.search(normalized[match.end() :])
        )
        if previous_negated_end is not None and re.fullmatch(
            r"\s*(?:(?:or|and)\s*)?", normalized[previous_negated_end : match.start()]
        ):
            # A parenthetical alias must not undo "without type 2 diabetes".
            negated = True
        if not negated:
            return True
        previous_negated_end = match.end()
    return False


def has_disease_label(conditions: Any) -> bool:
    """Match explicit type 2 labels without inferring a participant diagnosis.

    Generic/other diabetes labels and explicitly negated mentions do not match.
    This bounded lexical check is not a clinical screen or a complete negation
    parser, and intentionally differs from registry synonym-expanded search.
    """
    return isinstance(conditions, list) and any(
        isinstance(label, str) and _matches_label(label) for label in conditions
    )
