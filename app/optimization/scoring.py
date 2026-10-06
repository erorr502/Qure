from collections import Counter

from app.models import (
    CandidateDrug,
    DrugInteraction,
    OptimizationWeights,
)


def interaction_penalty(
    selected: list[CandidateDrug],
    interactions: list[DrugInteraction],
):

    selected_ids = {
        drug.rxcui
        for drug in selected
    }

    penalty = 0.0

    for interaction in interactions:

        if (
            interaction.drug_a in selected_ids
            and interaction.drug_b in selected_ids
        ):

            severity = interaction.severity.upper()

            if severity == "MODERATE":
                penalty += 1.0

            elif severity == "LOW":
                penalty += 0.25

    return penalty


def redundancy_penalty(
    selected: list[CandidateDrug],
):

    groups = [
        drug.therapeutic_class
        for drug in selected
        if drug.therapeutic_class
    ]

    counts = Counter(groups)

    return sum(
        max(count - 1, 0)
        for count in counts.values()
    )


def calculate_cost(
    selected,
    interactions,
    weights: OptimizationWeights,
):

    return round(
        weights.medication_count
        * len(selected)
        +
        weights.interaction
        * interaction_penalty(
            selected,
            interactions
        )
        +
        weights.redundancy
        * redundancy_penalty(
            selected
        ),
        3,
    )