from pydantic import BaseModel, Field


class PatientCase(BaseModel):
    conditions: list[str]
    contraindication_flags: list[str] = []
    max_medications: int = Field(
        default=3,
        ge=1,
        le=8,
    )


class CandidateDrug(BaseModel):
    rxcui: str
    name: str
    generic_name: str | None = None
    conditions_treated: list[str] = []
    contraindications: list[str] = []
    therapeutic_class: str | None = None
    substance_names: list[str] = []
    interaction_text: str = ""
    source: str | None = None
    spl_set_id: str | None = None


class DrugInteraction(BaseModel):
    drug_a: str
    drug_b: str
    severity: str
    description: str | None = None
    source: str | None = None


class OptimizationWeights(BaseModel):
    medication_count: float = 3.0
    interaction: float = 5.0
    redundancy: float = 2.0


class OptimizationRequest(BaseModel):
    patient: PatientCase
    candidate_drugs: list[CandidateDrug]
    interactions: list[DrugInteraction] = []
    weights: OptimizationWeights = OptimizationWeights()
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    shots: int = Field(
        default=2048,
        ge=256,
        le=8192,
    )


class RealOptimizationRequest(BaseModel):
    patient: PatientCase
    candidate_rxcuis: list[str] = Field(
        min_length=1,
        max_length=8,
    )
    weights: OptimizationWeights = OptimizationWeights()
    top_k: int = Field(
        default=3,
        ge=1,
        le=10,
    )
    shots: int = Field(
        default=2048,
        ge=256,
        le=8192,
    )