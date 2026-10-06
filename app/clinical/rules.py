from app.models import (
    CandidateDrug,
    DrugInteraction,
    PatientCase,
)


def decode_state(state: str, drugs: list[CandidateDrug]):
    return [
        drug
        for bit, drug in zip(state, drugs)
        if bit == "1"
    ]


def covers_conditions(
    selected: list[CandidateDrug],
    conditions: list[str],
) -> bool:

    for condition in conditions:
        if not any(
            condition in drug.conditions_treated
            for drug in selected
        ):
            return False

    return True


def has_contraindication(
    selected: list[CandidateDrug],
    patient: PatientCase,
) -> bool:

    patient_flags = set(
        patient.contraindication_flags
    )

    for drug in selected:
        if patient_flags.intersection(
            drug.contraindications
        ):
            return True

    return False


def has_forbidden_interaction(
    selected: list[CandidateDrug],
    interactions: list[DrugInteraction],
) -> bool:

    selected_ids = {
        drug.rxcui
        for drug in selected
    }

    for interaction in interactions:

        if interaction.severity.upper() != "FORBIDDEN":
            continue

        if (
            interaction.drug_a in selected_ids
            and interaction.drug_b in selected_ids
        ):
            return True

    return False


def evaluate_state(
    state: str,
    patient: PatientCase,
    drugs: list[CandidateDrug],
    interactions: list[DrugInteraction],
):

    selected = decode_state(
        state,
        drugs
    )

    violations = []

    if not covers_conditions(
        selected,
        patient.conditions,
    ):
        violations.append(
            "INSUFFICIENT_COVERAGE"
        )

    if has_contraindication(
        selected,
        patient,
    ):
        violations.append(
            "PATIENT_CONTRAINDICATION"
        )

    if has_forbidden_interaction(
        selected,
        interactions,
    ):
        violations.append(
            "FORBIDDEN_INTERACTION"
        )

    if len(selected) > patient.max_medications:
        violations.append(
            "MAX_MEDICATION_LIMIT"
        )

    return {
        "state": state,
        "selected_drugs": [
            drug.name for drug in selected
        ],
        "feasible": len(violations) == 0,
        "violations": violations,
    }
