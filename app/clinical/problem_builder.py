from itertools import product

from app.clinical.rules import evaluate_state


def generate_states(num_drugs: int):
    return [
        "".join(bits)
        for bits in product(
            "01",
            repeat=num_drugs
        )
    ]


def build_clinical_problem(
    patient,
    drugs,
    interactions,
):

    states = generate_states(
        len(drugs)
    )

    evaluated = [
        evaluate_state(
            state,
            patient,
            drugs,
            interactions,
        )
        for state in states
    ]

    feasible = [
        item
        for item in evaluated
        if item["feasible"]
    ]

    rejected = [
        item
        for item in evaluated
        if not item["feasible"]
    ]

    return {
        "num_drugs": len(drugs),
        "search_space": len(states),
        "feasible_states": feasible,
        "rejected_states": rejected,
    }