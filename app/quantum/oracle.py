from qiskit import QuantumCircuit


def build_phase_oracle(
    num_qubits: int,
    marked_states: list[str],
) -> QuantumCircuit:

    oracle = QuantumCircuit(
        num_qubits
    )

    for state in marked_states:

        if len(state) != num_qubits:
            raise ValueError(
                "Marked-state length "
                "does not match qubit count"
            )

        bits = state[::-1]

        zero_qubits = [
            index
            for index, bit
            in enumerate(bits)
            if bit == "0"
        ]

        for qubit in zero_qubits:
            oracle.x(qubit)

        if num_qubits == 1:

            oracle.z(0)

        else:

            target = num_qubits - 1

            controls = list(
                range(
                    num_qubits - 1
                )
            )

            oracle.h(target)

            oracle.mcx(
                controls,
                target,
            )

            oracle.h(target)

        for qubit in zero_qubits:
            oracle.x(qubit)

    return oracle