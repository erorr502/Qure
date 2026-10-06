import httpx


RXNORM_BASE_URL = (
    "https://rxnav.nlm.nih.gov/REST"
)


PREFERRED_TTYS = {
    "SCD",
    "SBD",
    "GPCK",
    "BPCK",
}


async def search_drugs(
    name: str,
) -> list[dict]:

    url = (
        f"{RXNORM_BASE_URL}/drugs.json"
    )

    async with httpx.AsyncClient(
        timeout=20.0
    ) as client:

        response = await client.get(
            url,
            params={
                "name": name
            },
        )

        response.raise_for_status()

    payload = response.json()

    groups = (
        payload
        .get("drugGroup", {})
        .get("conceptGroup", [])
    )

    results = []

    for group in groups:

        tty = group.get("tty")

        concepts = (
            group.get(
                "conceptProperties"
            )
            or []
        )

        for concept in concepts:

            results.append(
                {
                    "rxcui":
                        concept.get(
                            "rxcui"
                        ),

                    "name":
                        concept.get(
                            "name"
                        ),

                    "synonym":
                        concept.get(
                            "synonym"
                        ),

                    "tty":
                        tty,
                }
            )

    results.sort(
        key=lambda item: (
            item["tty"]
            not in PREFERRED_TTYS,

            item["name"]
            or "",
        )
    )

    return results


async def get_rxnorm_properties(
    rxcui: str,
) -> dict | None:

    url = (
        f"{RXNORM_BASE_URL}/"
        f"rxcui/{rxcui}/"
        f"properties.json"
    )

    async with httpx.AsyncClient(
        timeout=20.0
    ) as client:

        response = await client.get(
            url
        )

    if response.status_code == 404:
        return None

    response.raise_for_status()

    return response.json().get(
        "properties"
    )