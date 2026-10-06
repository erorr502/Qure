import httpx

OPENFDA_LABEL_URL = "https://api.fda.gov/drug/label.json"


async def _request_openfda(search: str) -> dict | None:
    params = {
        "search": search,
        "limit": 1,
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(
            OPENFDA_LABEL_URL,
            params=params,
        )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    payload = response.json()
    results = payload.get("results", [])

    if not results:
        return None

    return results[0]


async def get_label_by_rxcui(
    rxcui: str,
) -> dict | None:
    return await _request_openfda(
        f'openfda.rxcui:"{rxcui}"'
    )


async def get_label_by_generic_name(
    name: str,
) -> dict | None:
    clean_name = name.strip()

    if not clean_name:
        return None

    return await _request_openfda(
        f'openfda.generic_name:"{clean_name}"'
    )


async def get_label_by_substance(
    name: str,
) -> dict | None:
    clean_name = name.strip()

    if not clean_name:
        return None

    return await _request_openfda(
        f'openfda.substance_name:"{clean_name}"'
    )


def _combine_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            str(item)
            for item in value
        )

    return str(value)


def normalize_label(
    label: dict,
) -> dict:
    openfda = label.get(
        "openfda",
        {}
    )

    generic_names = openfda.get(
        "generic_name",
        []
    )

    brand_names = openfda.get(
        "brand_name",
        []
    )

    spl_set_ids = openfda.get(
        "spl_set_id",
        []
    )

    return {
        "generic_name": (
            generic_names[0]
            if generic_names
            else None
        ),

        "brand_name": (
            brand_names[0]
            if brand_names
            else None
        ),

        "rxcui": openfda.get(
            "rxcui",
            []
        ),

        "substance_name": openfda.get(
            "substance_name",
            []
        ),

        "pharmacologic_class": openfda.get(
            "pharm_class_epc",
            []
        ),

        "indications_text": _combine_text(
            label.get(
                "indications_and_usage"
            )
        ),

        "contraindications_text": _combine_text(
            label.get(
                "contraindications"
            )
        ),

        "drug_interactions_text": _combine_text(
            label.get(
                "drug_interactions"
            )
        ),

        "warnings_text": _combine_text(
            label.get(
                "warnings"
            )
        ),

        "boxed_warning_text": _combine_text(
            label.get(
                "boxed_warning"
            )
        ),

        "source": "openFDA Drug Label API",

        "spl_set_id": (
            spl_set_ids[0]
            if spl_set_ids
            else None
        ),
    }