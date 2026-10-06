from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.classical.baseline import solve_classically
from app.clinical.problem_builder import build_clinical_problem
from app.local_data import CONDITION_LABELS, build_request, catalog, condition_label
from app.models import OptimizationWeights
from app.quantum.adaptive import run_adaptive_search

router = APIRouter(prefix="/api/local", tags=["bundled dataset"])


class LocalOptimizationRequest(BaseModel):
    conditions: list[str] = Field(min_length=1)
    candidate_drugs: list[str] | None = None
    max_medications: int = Field(default=6, ge=1, le=10)
    top_k: int = Field(default=5, ge=1, le=10)
    shots: int = Field(default=1024, ge=256, le=4096)
    weights: OptimizationWeights = OptimizationWeights()


@router.get("/catalog")
def get_catalog():
    return catalog()


@router.post("/optimize")
def optimize_local(request: LocalOptimizationRequest):
    try:
        patient, drugs, interactions = build_request(
            request.conditions,
            request.candidate_drugs,
            request.max_medications,
        )
        problem = build_clinical_problem(patient, drugs, interactions)
        classical = solve_classically(
            problem["feasible_states"], drugs, interactions, request.weights
        )
        quantum = run_adaptive_search(
            problem["feasible_states"], drugs, interactions, request.weights,
            shots=request.shots,
        )
        classical_best = classical[0] if classical else None
        quantum_best = quantum["best"]
        matches = bool(
            classical_best and quantum_best
            and classical_best["cost"] == quantum_best["cost"]
        )
        n = len(drugs)
        m = len(problem["feasible_states"])
        import math
        theoretical = (math.pi / 4 * math.sqrt((2 ** n) / m)) if m else None
        return {
            "status": "completed",
            "mode": "BUNDLED_DAILYMED_GROVER",
            "data_provenance": {
                "drug_indications": "DailyMed-derived benchmark CSV",
                "interactions": "DailyMed-derived benchmark CSV",
                "patient_instance": "synthetic research benchmark",
            },
            "conditions": [
                {"id": c, "label": condition_label(c)} for c in request.conditions
            ],
            "candidate_drugs": [d.name for d in drugs],
            "selection_basis": {
                "type": "condition_coverage",
                "message": "Candidate drugs were selected from verified catalog coverage for the patient's requested conditions.",
                "requested_conditions": [condition_label(c) for c in request.conditions],
            },
            "problem": {
                "candidate_drugs": n,
                "search_space": 2 ** n,
                "feasible_states": m,
                "rejected_states": len(problem["rejected_states"]),
                "max_medications": request.max_medications,
            },
            "classical": {
                "best": classical_best,
                "top_candidates": classical[:request.top_k],
                "exhaustive_states_checked": 2 ** n,
                "complexity_label": "O(N) exhaustive search",
            },
            "quantum": {
                "best": quantum_best,
                "metrics": quantum["quantum_metrics"],
                "history": quantum["history"],
                "theoretical_single_round_iterations": round(theoretical, 2) if theoretical else None,
                "complexity_label": "O(√N) Grover query complexity (theoretical)",
            },
            "verification": {
                "classical_best": classical_best,
                "quantum_best": quantum_best,
                "cost_matches": matches,
            },
            "notes": [
                "Quantum and classical methods use the same constraints and candidate space.",
                "The classical solver is a benchmark/verification baseline, not a second product mode.",
                "Grover's O(√N) advantage is query-complexity theory; this prototype does not claim real-world wall-clock speedup.",
                "Results are a computational research prototype and not clinical advice or a prescription.",
            ],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Local QSafeRx optimization failed: {exc}")

# ---------------------------------------------------------
# PATIENT DATABASE
# ---------------------------------------------------------

from app.patient_store import create_patient, get_patient, list_patients, update_patient
from pydantic import BaseModel, Field


class PatientRecordRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    sex: str = Field(min_length=1, max_length=40)
    age: int = Field(ge=0, le=120)
    conditions: list[str] = Field(min_length=1)
    pill_limit: int = Field(default=3, ge=1, le=8)


@router.get("/patients")
def patients():
    return {"patients": list_patients()}


@router.post("/patients", status_code=201)
def add_patient(request: PatientRecordRequest):
    try:
        return create_patient(request.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.put("/patients/{patient_id}")
def edit_patient(patient_id: str, request: PatientRecordRequest):
    try:
        updated = update_patient(patient_id, request.model_dump())
        if updated is None:
            raise HTTPException(status_code=404, detail="Patient not found")
        return updated
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
