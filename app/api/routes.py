import asyncio

from fastapi import APIRouter, HTTPException, Query

from app.data.rxnorm import search_drugs
from app.data.drug_knowledge import (
    enrich_drug,
    verified_search,
)

from app.models import (
    OptimizationRequest,
    RealOptimizationRequest,
)

from app.clinical.normalizer import (
    normalize_clinical_drug,
)

from app.clinical.interactions import (
    build_interaction_matrix,
)

from app.clinical.dedup import (
    deduplicate_drugs,
)

from app.clinical.problem_builder import (
    build_clinical_problem,
)

from app.classical.baseline import (
    solve_classically,
)

from app.quantum.adaptive import (
    run_adaptive_search,
)


router = APIRouter(prefix="/api")


# ---------------------------------------------------------
# DRUG SEARCH
# ---------------------------------------------------------

@router.get("/drugs/search")
async def drug_search(
    q: str = Query(..., min_length=2),
):
    try:
        results = await search_drugs(q)

        return {
            "query": q,
            "count": len(results),
            "results": results[:20],
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"RxNorm lookup failed: {exc}",
        )


# ---------------------------------------------------------
# VERIFIED DRUG SEARCH
# ---------------------------------------------------------

@router.get("/drugs/verified-search")
async def verified_drug_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(
        default=8,
        ge=1,
        le=8,
    ),
):
    try:
        results = await verified_search(
            query=q,
            limit=limit,
        )

        return {
            "query": q,
            "verified_count": len(results),
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Verified drug search failed: {exc}",
        )


# ---------------------------------------------------------
# SINGLE DRUG CLINICAL DATA
# ---------------------------------------------------------

@router.get("/drugs/{rxcui}/clinical-data")
async def drug_clinical_data(
    rxcui: str,
    name: str | None = None,
):
    try:
        return await enrich_drug(
            rxcui=rxcui,
            name=name,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Clinical data lookup failed: {exc}",
        )


# ---------------------------------------------------------
# CLASSICAL OPTIMIZATION
# ---------------------------------------------------------

@router.post("/optimize/classical")
async def optimize_classically(
    request: OptimizationRequest,
):
    try:
        problem = build_clinical_problem(
            request.patient,
            request.candidate_drugs,
            request.interactions,
        )

        ranked = solve_classically(
            problem["feasible_states"],
            request.candidate_drugs,
            request.interactions,
            request.weights,
        )

        return {
            "status": "completed",
            "mode": "classical",

            "problem": {
                "candidate_drugs": len(
                    request.candidate_drugs
                ),
                "search_space": problem[
                    "search_space"
                ],
                "feasible_states": len(
                    problem["feasible_states"]
                ),
                "rejected_states": len(
                    problem["rejected_states"]
                ),
            },

            "top_candidates": ranked[
                :request.top_k
            ],
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Classical optimization failed: {exc}",
        )


# ---------------------------------------------------------
# MANUAL-DATA QUANTUM OPTIMIZATION
# ---------------------------------------------------------

@router.post("/optimize")
async def optimize(
    request: OptimizationRequest,
):
    try:
        problem = build_clinical_problem(
            request.patient,
            request.candidate_drugs,
            request.interactions,
        )

        classical = solve_classically(
            problem["feasible_states"],
            request.candidate_drugs,
            request.interactions,
            request.weights,
        )

        quantum = run_adaptive_search(
            problem["feasible_states"],
            request.candidate_drugs,
            request.interactions,
            request.weights,
            shots=request.shots,
        )

        classical_best = (
            classical[0]
            if classical
            else None
        )

        quantum_best = quantum["best"]

        cost_matches = (
            classical_best is not None
            and quantum_best is not None
            and classical_best["cost"]
            == quantum_best["cost"]
        )

        return {
            "status": "completed",
            "mode": "quantum",

            "problem": {
                "candidate_drugs": len(
                    request.candidate_drugs
                ),
                "search_space": problem[
                    "search_space"
                ],
                "feasible_states": len(
                    problem["feasible_states"]
                ),
                "rejected_states": len(
                    problem["rejected_states"]
                ),
            },

            "quantum_result": quantum_best,

            "top_candidates": classical[
                :request.top_k
            ],

            "adaptive_search": quantum[
                "history"
            ],

            "quantum_metrics": quantum[
                "quantum_metrics"
            ],

            "verification": {
                "classical_best": classical_best,
                "quantum_best": quantum_best,
                "cost_matches": cost_matches,
            },
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Quantum optimization failed: {exc}",
        )


# ---------------------------------------------------------
# REAL-DATA END-TO-END QURE OPTIMIZATION
# ---------------------------------------------------------

@router.post("/optimize/real")
async def optimize_real(
    request: RealOptimizationRequest,
):
    try:
        # ---------------------------------------------
        # 1. Validate number of submitted drugs
        # ---------------------------------------------

        if len(request.candidate_rxcuis) > 8:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Qure MVP supports a maximum "
                    "of 8 candidate drugs."
                ),
            )

        # ---------------------------------------------
        # 2. Retrieve exact-label clinical data
        # ---------------------------------------------

        details = await asyncio.gather(
            *[
                enrich_drug(rxcui)
                for rxcui
                in request.candidate_rxcuis
            ],
            return_exceptions=True,
        )

        failed_drugs = []
        verified_details = []

        for rxcui, detail in zip(
            request.candidate_rxcuis,
            details,
        ):
            if isinstance(
                detail,
                Exception,
            ):
                failed_drugs.append(
                    {
                        "rxcui": rxcui,
                        "reason": str(detail),
                    }
                )
                continue

            if not detail.get(
                "label_found"
            ):
                failed_drugs.append(
                    {
                        "rxcui": rxcui,
                        "reason": detail.get(
                            "data_status",
                            "LABEL_NOT_AVAILABLE",
                        ),
                    }
                )
                continue

            verified_details.append(
                detail
            )

        if failed_drugs:
            raise HTTPException(
                status_code=422,
                detail={
                    "message": (
                        "All candidate drugs must "
                        "have an exact verified FDA "
                        "label before optimization."
                    ),
                    "failed_drugs": failed_drugs,
                },
            )

        # ---------------------------------------------
        # 3. Normalize FDA label data
        # ---------------------------------------------

        normalized_drugs = [
            normalize_clinical_drug(
                detail
            )
            for detail
            in verified_details
        ]

        # ---------------------------------------------
        # 4. Remove equivalent duplicate products
        # ---------------------------------------------

        drugs, duplicates_removed = (
            deduplicate_drugs(
                normalized_drugs
            )
        )

        if not drugs:
            raise HTTPException(
                status_code=422,
                detail=(
                    "No unique candidate drugs "
                    "remain after normalization "
                    "and duplicate removal."
                ),
            )

        # ---------------------------------------------
        # 5. Build drug interaction matrix
        # ---------------------------------------------

        interactions = (
            build_interaction_matrix(
                drugs
            )
        )

        # ---------------------------------------------
        # 6. Build clinical optimization problem
        # ---------------------------------------------

        problem = build_clinical_problem(
            request.patient,
            drugs,
            interactions,
        )

        # ---------------------------------------------
        # 7. Classical verification baseline
        # ---------------------------------------------

        classical = solve_classically(
            problem["feasible_states"],
            drugs,
            interactions,
            request.weights,
        )

        # ---------------------------------------------
        # 8. Quantum adaptive search
        # ---------------------------------------------

        quantum = run_adaptive_search(
            problem["feasible_states"],
            drugs,
            interactions,
            request.weights,
            shots=request.shots,
        )

        classical_best = (
            classical[0]
            if classical
            else None
        )

        quantum_best = quantum[
            "best"
        ]

        cost_matches = (
            classical_best is not None
            and quantum_best is not None
            and classical_best["cost"]
            == quantum_best["cost"]
        )

        # ---------------------------------------------
        # 9. Final frontend-ready response
        # ---------------------------------------------

        return {
            "status": "completed",

            "mode": "REAL_DATA_QUANTUM",

            "data_provenance": {
                "drug_identity": "RxNorm",
                "clinical_labels": (
                    "openFDA FDA drug labels"
                ),
                "match_policy": (
                    "exact RxCUI only"
                ),
                "normalization": (
                    "deterministic rule-based"
                ),
            },

            "clinical_model": {
                "conditions": (
                    request.patient.conditions
                ),

                "contraindication_flags": (
                    request.patient
                    .contraindication_flags
                ),

                "submitted_drug_count": len(
                    request.candidate_rxcuis
                ),

                "unique_drug_count": len(
                    drugs
                ),

                "duplicates_removed": len(
                    duplicates_removed
                ),

                "interaction_rules_found": len(
                    interactions
                ),
            },

            "duplicate_products_removed": (
                duplicates_removed
            ),

            "normalized_drugs": [
                drug.model_dump()
                for drug in drugs
            ],

            "interactions": [
                interaction.model_dump()
                for interaction
                in interactions
            ],

            "problem": {
                "search_space": problem[
                    "search_space"
                ],

                "feasible_states": len(
                    problem[
                        "feasible_states"
                    ]
                ),

                "rejected_states": len(
                    problem[
                        "rejected_states"
                    ]
                ),
            },

            "top_candidates": classical[
                :request.top_k
            ],

            "quantum_result": (
                quantum_best
            ),

            "adaptive_search": quantum[
                "history"
            ],

            "quantum_metrics": quantum[
                "quantum_metrics"
            ],

            "verification": {
                "classical_best": (
                    classical_best
                ),

                "quantum_best": (
                    quantum_best
                ),

                "cost_matches": (
                    cost_matches
                ),
            },

            "disclaimer": (
                "Research and decision-support "
                "prototype only. Not for "
                "autonomous prescribing."
            ),
        }

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=(
                "Real-data optimization "
                f"failed: {exc}"
            ),
        )