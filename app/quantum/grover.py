import math

from qiskit import QuantumCircuit
from qiskit.circuit.library import grover_operator
from qiskit.primitives import StatevectorSampler

from app.quantum.oracle import build_phase_oracle


def optimal_iterations(
    num_qubits: int,
    marked_count: int,
) -> int:

    total_states = 2 ** num_qubits

    if marked_count <= 0:
        return 0

    if marked_count >= total_states:
        return 0

    theta = math.asin(
        math.sqrt(
            marked_count / total_states
        )
    )

    iterations = math.floor(
        math.pi / (4 * theta)
    )

    # IMPORTANT:
    # Do NOT force one Grover iteration.
    # When a large fraction of states is marked,
    # zero iterations can be optimal.
    return max(iterations, 0)


def run_grover(
    num_qubits: int,
    marked_states: list[str],
    shots: int = 2048,
) -> dict:

    if not marked_states:
        return {
            "counts": {},
            "best_state": None,
            "iterations": 0,
            "circuit_depth": 0,
            "gate_counts": {},
            "marked_probability": 0.0,
        }

    oracle = build_phase_oracle(
        num_qubits,
        marked_states,
    )

    operator = grover_operator(
        oracle
    )

    iterations = optimal_iterations(
        num_qubits,
        len(marked_states),
    )

    circuit = QuantumCircuit(
        num_qubits
    )

    # Uniform superposition
    circuit.h(
        range(num_qubits)
    )

    if iterations > 0:
        circuit.compose(
            operator.power(iterations),
            inplace=True,
        )

    circuit.measure_all()

    sampler = StatevectorSampler(
        seed=42
    )

    job = sampler.run(
        [circuit],
        shots=shots,
    )

    result = job.result()

    raw_counts = (
        result[0]
        .data
        .meas
        .get_counts()
    )

    # Qiskit measurement strings already correspond
    # to the state-string convention used by Qure.
    counts = {
        state: int(count)
        for state, count
        in raw_counts.items()
    }

    marked_set = set(
        marked_states
    )

    marked_counts = {
        state: count
        for state, count
        in counts.items()
        if state in marked_set
    }

    best_state = None

    if marked_counts:
        best_state = max(
            marked_counts,
            key=marked_counts.get,
        )

    marked_shots = sum(
        marked_counts.values()
    )

    marked_probability = (
        marked_shots / shots
        if shots > 0
        else 0.0
    )

    return {
        "counts": counts,
        "best_state": best_state,
        "iterations": iterations,
        "circuit_depth": circuit.depth(),
        "gate_counts": {
            str(key): int(value)
            for key, value
            in circuit.count_ops().items()
        },
        "marked_probability": round(
            marked_probability,
            6,
        ),
    }