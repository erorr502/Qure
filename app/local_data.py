from __future__ import annotations

import csv
import json
from functools import lru_cache
from pathlib import Path

from app.models import CandidateDrug, DrugInteraction, PatientCase

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

CONDITION_LABELS = {
    "heart_failure": "Heart failure",
    "hypertension": "Hypertension",
    "atrial_fibrillation": "Atrial fibrillation",
    "type2_diabetes": "Type 2 diabetes",
    "hyperlipidemia": "Hyperlipidemia",
    "gastroesophageal_reflux_disease": "GERD",
}


def _split(value: str) -> list[str]:
    return [x.strip() for x in (value or "").split(";") if x.strip()]


def condition_label(condition_id: str) -> str:
    """Return a display label for built-in or user-defined patient conditions."""
    if condition_id in CONDITION_LABELS:
        return CONDITION_LABELS[condition_id]
    if condition_id.startswith("custom:"):
        return condition_id[7:].strip() or "Custom condition"
    return condition_id.replace("_", " ").strip().title()


def normalize_custom_condition(value: str) -> str:
    """Store free-text health conditions safely while preserving the user's wording."""
    label = " ".join(str(value or "").strip().split())
    if not label:
        raise ValueError("Condition name cannot be empty.")
    if len(label) > 120:
        raise ValueError("Condition name must be 120 characters or fewer.")
    # Known catalog IDs remain IDs; everything else is explicitly marked custom.
    if label in CONDITION_LABELS or label.startswith("custom:"):
        return label
    return f"custom:{label}"


@lru_cache(maxsize=1)
def load_local_dataset() -> dict:
    with (DATA / "coverage_matrix.csv").open(newline="", encoding="utf-8") as f:
        coverage_rows = list(csv.DictReader(f))
    with (DATA / "drugs_real_dailymed.csv").open(newline="", encoding="utf-8") as f:
        drug_rows = {r["drug"]: r for r in csv.DictReader(f)}
    with (DATA / "interactions_real_dailymed.csv").open(newline="", encoding="utf-8") as f:
        interaction_rows = list(csv.DictReader(f))
    with (DATA / "patient_instance.json").open(encoding="utf-8") as f:
        patient = json.load(f)

    drugs: list[CandidateDrug] = []
    for row in coverage_rows:
        name = row["drug"]
        meta = drug_rows.get(name, {})
        treated = [c for c in CONDITION_LABELS if row.get(c) == "1"]
        drugs.append(
            CandidateDrug(
                rxcui=name,
                name=name,
                generic_name=name,
                conditions_treated=treated,
                contraindications=[],
                therapeutic_class=None,
                substance_names=[name],
                interaction_text="",
                source="DailyMed benchmark dataset",
                spl_set_id=meta.get("source_ref"),
            )
        )

    interactions: list[DrugInteraction] = []
    for row in interaction_rows:
        severity = row["severity"].lower()
        # The local benchmark defines high severity as a hard constraint.
        mapped = "FORBIDDEN" if severity == "high" else severity.upper()
        interactions.append(
            DrugInteraction(
                drug_a=row["drug_a"],
                drug_b=row["drug_b"],
                severity=mapped,
                description=row.get("label_evidence"),
                source=row.get("source"),
            )
        )

    return {
        "drugs": drugs,
        "interactions": interactions,
        "patient": patient,
    }


def catalog() -> dict:
    ds = load_local_dataset()
    drugs = []
    for d in ds["drugs"]:
        drugs.append({
            "name": d.name,
            "conditions": d.conditions_treated,
            "condition_labels": [CONDITION_LABELS[c] for c in d.conditions_treated],
            "source": d.source,
        })
    interactions = [
        {
            "drug_a": x.drug_a,
            "drug_b": x.drug_b,
            "severity": x.severity,
            "description": x.description,
            "source": x.source,
        }
        for x in ds["interactions"]
    ]
    return {
        "drugs": drugs,
        "conditions": [
            {"id": k, "label": v} for k, v in CONDITION_LABELS.items()
        ],
        "interactions": interactions,
        "benchmark": ds["patient"],
    }


def build_request(
    conditions: list[str],
    candidate_names: list[str] | None,
    max_medications: int,
) -> tuple[PatientCase, list[CandidateDrug], list[DrugInteraction]]:
    ds = load_local_dataset()
    by_name = {d.name: d for d in ds["drugs"]}

    # Personalize the candidate pool to the patient's selected conditions.
    # If the caller supplies an explicit candidate list, respect it (after validation).
    # Otherwise only drugs mapped to at least one requested condition enter the
    # optimization search space. This prevents unrelated medicines from appearing
    # as optimization candidates for a patient.
    if candidate_names:
        names = list(dict.fromkeys(candidate_names))
    else:
        names = [
            d.name
            for d in ds["drugs"]
            if any(condition in d.conditions_treated for condition in conditions)
        ]

        # Custom conditions are allowed in patient records, but the bundled
        # benchmark can only optimize conditions for which verified drug coverage
        # exists in its coverage matrix. Never invent a drug-condition mapping.
        unsupported = [
            str(c) for c in conditions
            if not any(c in d.conditions_treated for d in ds["drugs"])
        ]
        if unsupported:
            labels = ", ".join(condition_label(c) for c in unsupported)
            raise ValueError(
                f"No verified drug coverage is available in the bundled catalog for: {labels}. "
                "The condition can still be saved to the patient, but add verified drug-coverage data before optimization."
            )

    missing = [n for n in names if n not in by_name]
    if missing:
        raise ValueError(f"Unknown candidate drugs: {', '.join(missing)}")
    if len(names) < 1 or len(names) > 10:
        raise ValueError("Choose between 1 and 10 candidate drugs.")
    normalized_conditions = []
    for condition in conditions:
        value = str(condition).strip()
        if not value:
            continue
        if value in CONDITION_LABELS:
            normalized_conditions.append(value)
        elif value.startswith("custom:"):
            normalized_conditions.append(normalize_custom_condition(value))
        else:
            normalized_conditions.append(normalize_custom_condition(value))
    if not normalized_conditions:
        raise ValueError("Select at least one required condition.")
    patient = PatientCase(
        conditions=normalized_conditions,
        contraindication_flags=[],
        max_medications=max_medications,
    )
    drugs = [by_name[n] for n in names]
    selected = set(names)
    interactions = [
        x for x in ds["interactions"]
        if x.drug_a in selected and x.drug_b in selected
    ]
    return patient, drugs, interactions
