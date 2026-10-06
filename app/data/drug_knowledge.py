import asyncio

from app.data.openfda import (
    get_label_by_rxcui,
    normalize_label,
)

from app.data.rxnorm import (
    get_rxnorm_properties,
    search_drugs,
)


async def enrich_drug(
    rxcui: str,
    name: str | None = None,
) -> dict:

    properties = await get_rxnorm_properties(
        rxcui
    )

    rxnorm_name = (
        properties.get("name")
        if properties
        and properties.get("name")
        else name or rxcui
    )

    label = await get_label_by_rxcui(
        rxcui
    )

    if label is None:

        return {
            "rxcui": rxcui,

            "name": rxnorm_name,

            "requested_name":
                name,

            "label_found":
                False,

            "lookup_method":
                "RXCUI_EXACT",

            "data_status":
                "LABEL_NOT_AVAILABLE_FOR_RXCUI",

            "generic_name":
                None,

            "therapeutic_class":
                None,

            "substance_names":
                [],

            "indications_text":
                "",

            "contraindications_text":
                "",

            "drug_interactions_text":
                "",

            "warnings_text":
                "",

            "boxed_warning_text":
                "",

            "source":
                None,

            "spl_set_id":
                None,
        }

    normalized = normalize_label(
        label
    )

    classes = normalized.get(
        "pharmacologic_class",
        [],
    )

    return {
        "rxcui": rxcui,

        "name":
            rxnorm_name,

        "requested_name":
            name,

        "label_found":
            True,

        "lookup_method":
            "RXCUI_EXACT",

        "data_status":
            "VERIFIED",

        "generic_name":
            normalized[
                "generic_name"
            ],

        "therapeutic_class": (
            classes[0]
            if classes
            else None
        ),

        "substance_names":
            normalized.get(
                "substance_name",
                [],
            ),

        "indications_text":
            normalized[
                "indications_text"
            ],

        "contraindications_text":
            normalized[
                "contraindications_text"
            ],

        "drug_interactions_text":
            normalized[
                "drug_interactions_text"
            ],

        "warnings_text":
            normalized[
                "warnings_text"
            ],

        "boxed_warning_text":
            normalized[
                "boxed_warning_text"
            ],

        "source":
            normalized[
                "source"
            ],

        "spl_set_id":
            normalized[
                "spl_set_id"
            ],
    }


async def verified_search(
    query: str,
    limit: int = 8,
    scan: int = 20,
) -> list[dict]:

    concepts = await search_drugs(
        query
    )

    concepts = concepts[
        :max(scan, limit)
    ]

    tasks = [
        enrich_drug(
            concept["rxcui"],
            concept["name"],
        )
        for concept in concepts
        if concept.get("rxcui")
    ]

    enriched = await asyncio.gather(
        *tasks,
        return_exceptions=True,
    )

    verified = []

    for concept, detail in zip(
        concepts,
        enriched,
    ):

        if isinstance(
            detail,
            Exception,
        ):
            continue

        if not detail.get(
            "label_found"
        ):
            continue

        verified.append(
            {
                "rxcui":
                    detail["rxcui"],

                "name":
                    detail["name"],

                "generic_name":
                    detail[
                        "generic_name"
                    ],

                "therapeutic_class":
                    detail[
                        "therapeutic_class"
                    ],

                "substance_names":
                    detail[
                        "substance_names"
                    ],

                "data_status":
                    "VERIFIED",

                "source":
                    detail["source"],

                "spl_set_id":
                    detail["spl_set_id"],

                "tty":
                    concept.get("tty"),
            }
        )

        if len(verified) >= limit:
            break

    return verified