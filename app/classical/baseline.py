from app.clinical.rules import decode_state
from app.optimization.scoring import calculate_cost


def solve_classically(
    feasible_states,
    drugs,
    interactions,
    weights,
):

    results = []

    for item in feasible_states:

        state = item["state"]

        selected = decode_state(
            state,
            drugs
        )

        cost = calculate_cost(
            selected,
            interactions,
            weights
        )

        results.append(
            {
                "state": state,
                "drugs": [
                    drug.name
                    for drug in selected
                ],
                "cost": cost,
            }
        )

    return sorted(
        results,
        key=lambda x: x["cost"]
    )