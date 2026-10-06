import re
from itertools import combinations

from app.models import (
    CandidateDrug,
    DrugInteraction,
)


FORBIDDEN_CUES = (
    "contraindicated",
    "avoid concomitant use",
    "do not use",
    "should not be used",
)


MODERATE_CUES = (
    "monitor",
    "caution",
    "increased risk",
    "increase the risk",
    "may increase",
    "may decrease",
    "dose adjustment",
    "adjust the dose",
)


def _ingredient_names(
    drug: CandidateDrug,
) -> list[str]:

    names = list(
        drug.substance_names
    )

    if drug.generic_name:
        names.append(
            drug.generic_name
        )

    cleaned = []

    for name in names:

        if not name:
            continue

        parts = re.split(
            r"\band\b|/|\+",
            name,
            flags=re.IGNORECASE,
        )

        for part in parts:

            part = part.strip().lower()

            if len(part) >= 4:
                cleaned.append(part)

    return sorted(
        set(cleaned),
        key=len,
        reverse=True,
    )


def _find_context(
    text: str,
    needle: str,
    radius: int = 220,
) -> str | None:

    text = text or ""

    lower_text = text.lower()

    index = lower_text.find(
        needle.lower()
    )

    if index < 0:
        return None

    start = max(
        0,
        index - radius,
    )

    end = min(
        len(text),
        index + len(needle) + radius,
    )

    return text[start:end]


def _classify_severity(
    context: str,
) -> str:

    text = context.lower()

    if any(
        cue in text
        for cue in FORBIDDEN_CUES
    ):
        return "FORBIDDEN"

    if any(
        cue in text
        for cue in MODERATE_CUES
    ):
        return "MODERATE"

    return "LOW"


def build_interaction_matrix(
    drugs: list[CandidateDrug],
) -> list[DrugInteraction]:

    results = []

    for drug_a, drug_b in combinations(
        drugs,
        2,
    ):

        evidence = None
        source_drug = None

        for ingredient in _ingredient_names(
            drug_b
        ):

            evidence = _find_context(
                drug_a.interaction_text,
                ingredient,
            )

            if evidence:
                source_drug = drug_a
                break

        if evidence is None:

            for ingredient in _ingredient_names(
                drug_a
            ):

                evidence = _find_context(
                    drug_b.interaction_text,
                    ingredient,
                )

                if evidence:
                    source_drug = drug_b
                    break

        if evidence is None:
            continue

        results.append(
            DrugInteraction(
                drug_a=drug_a.rxcui,
                drug_b=drug_b.rxcui,

                severity=
                    _classify_severity(
                        evidence
                    ),

                description=
                    evidence.strip(),

                source=(
                    f"{source_drug.source}; "
                    f"SPL={source_drug.spl_set_id}"
                ),
            )
        )

    return results