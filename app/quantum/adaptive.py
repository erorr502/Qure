from app.clinical.rules import (
    decode_state,
)

from app.optimization.scoring import (
    calculate_cost,
)

from app.quantum.grover import (
    run_grover,
)


def run_adaptive_search(
    feasible_states,
    drugs,
    interactions,
    weights,
    shots: int = 2048,
):

    scored = []

    for item in feasible_states:

        state = item["state"]

        selected = decode_state(
            state,
            drugs,
        )

        scored.append(
            {
                "state":
                    state,

                "cost":
                    calculate_cost(
                        selected,
                        interactions,
                        weights,
                    ),

                "drugs": [
                    drug.name
                    for drug
                    in selected
                ],
            }
        )

    if not scored:

        return {
            "best": None,
            "history": [],
            "quantum_metrics": {},
        }

    threshold = (
        max(
            item["cost"]
            for item in scored
        )
        + 1.0
    )

    best = None

    history = []

    total_depth = 0

    total_grover_iterations = 0

    step = 0

    while True:

        eligible = [
            item
            for item in scored
            if item["cost"]
            < threshold
        ]

        if not eligible:
            break

        quantum = run_grover(
            num_qubits=len(drugs),

            marked_states=[
                item["state"]
                for item in eligible
            ],

            shots=shots,
        )

        measured = quantum[
            "best_state"
        ]

        if measured is None:
            break

        candidate = next(
            (
                item
                for item
                in eligible
                if item["state"]
                == measured
            ),
            None,
        )

        if candidate is None:
            break

        history.append(
            {
                "iteration":
                    step,

                "threshold":
                    threshold,

                "eligible_states":
                    len(eligible),

                "candidate_state":
                    candidate["state"],

                "candidate_cost":
                    candidate["cost"],

                "grover_iterations":
                    quantum[
                        "iterations"
                    ],
            }
        )

        total_depth += quantum[
            "circuit_depth"
        ]

        total_grover_iterations += (
            quantum["iterations"]
        )

        if (
            best is None
            or candidate["cost"]
            < best["cost"]
        ):
            best = candidate

            threshold = (
                candidate["cost"]
            )

            step += 1

        else:
            break

    return {
        "best":
            best,

        "history":
            history,

        "quantum_metrics": {
            "qubits":
                len(drugs),

            "shots":
                shots,

            "adaptive_rounds":
                len(history),

            "total_grover_iterations":
                total_grover_iterations,

            "aggregate_circuit_depth":
                total_depth,
        },
    }