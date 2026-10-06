from app.models import CandidateDrug


CONDITION_TERMS = {
    "type_2_diabetes": [
        "type 2 diabetes",
        "type 2 diabetes mellitus",
        "glycemic control",
        "glycaemic control",
    ],

    "hypertension": [
        "hypertension",
        "high blood pressure",
    ],

    "heart_failure": [
        "heart failure",
        "cardiac failure",
    ],

    "atrial_fibrillation": [
        "atrial fibrillation",
    ],

    "hyperlipidemia": [
        "hyperlipidemia",
        "hypercholesterolemia",
        "elevated cholesterol",
    ],
}


CONTRAINDICATION_TERMS = {
    "renal_impairment": [
        "severe renal impairment",
        "renal failure",
        "egfr below",
        "egfr <",
    ],

    "hepatic_impairment": [
        "severe hepatic impairment",
        "hepatic failure",
        "severe liver impairment",
    ],

    "hypersensitivity": [
        "serious hypersensitivity",
        "hypersensitivity reaction",
        "anaphylaxis",
        "angioedema",
    ],

    "metabolic_acidosis": [
        "metabolic acidosis",
        "diabetic ketoacidosis",
    ],
}


def _contains_any(
    text: str,
    terms: list[str],
) -> bool:

    text = (text or "").lower()

    return any(
        term.lower() in text
        for term in terms
    )


def normalize_clinical_drug(
    detail: dict,
) -> CandidateDrug:

    indications = detail.get(
        "indications_text",
        "",
    )

    contraindications_text = detail.get(
        "contraindications_text",
        "",
    )

    conditions_treated = [
        tag
        for tag, terms in CONDITION_TERMS.items()
        if _contains_any(
            indications,
            terms,
        )
    ]

    contraindications = [
        tag
        for tag, terms in CONTRAINDICATION_TERMS.items()
        if _contains_any(
            contraindications_text,
            terms,
        )
    ]

    return CandidateDrug(
        rxcui=detail["rxcui"],

        name=detail["name"],

        generic_name=detail.get(
            "generic_name"
        ),

        conditions_treated=
            conditions_treated,

        contraindications=
            contraindications,

        therapeutic_class=detail.get(
            "therapeutic_class"
        ),

        substance_names=detail.get(
            "substance_names",
            [],
        ),

        interaction_text=detail.get(
            "drug_interactions_text",
            "",
        ),

        source=detail.get(
            "source"
        ),

        spl_set_id=detail.get(
            "spl_set_id"
        ),
    )