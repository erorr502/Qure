import re

from app.models import CandidateDrug


def _normalize_name(name: str) -> str:
    """
    Remove branding in square brackets and normalize whitespace/case.

    Example:
    '... Extended Release Oral Tablet [Invokamet]'
    becomes
    '... extended release oral tablet'
    """

    name = name or ""

    name = re.sub(
        r"\[[^\]]+\]",
        "",
        name,
    )

    name = re.sub(
        r"\s+",
        " ",
        name,
    )

    return name.strip().lower()


def _normalize_substances(
    substances: list[str],
) -> tuple[str, ...]:

    return tuple(
        sorted(
            {
                item.strip().lower()
                for item in substances
                if item
            }
        )
    )


def drug_fingerprint(
    drug: CandidateDrug,
) -> tuple:

    return (
        _normalize_name(
            drug.name
        ),
        _normalize_substances(
            drug.substance_names
        ),
    )


def deduplicate_drugs(
    drugs: list[CandidateDrug],
) -> tuple[
    list[CandidateDrug],
    list[dict]
]:
    """
    Remove equivalent RxNorm representations of
    the same product before optimization.

    Returns:
      unique_drugs
      duplicate_records
    """

    unique = []

    duplicates = []

    seen = {}

    for drug in drugs:

        fingerprint = drug_fingerprint(
            drug
        )

        if fingerprint not in seen:

            seen[fingerprint] = drug

            unique.append(
                drug
            )

            continue

        original = seen[
            fingerprint
        ]

        duplicates.append(
            {
                "removed_rxcui":
                    drug.rxcui,

                "removed_name":
                    drug.name,

                "kept_rxcui":
                    original.rxcui,

                "kept_name":
                    original.name,

                "reason":
                    "EQUIVALENT_PRODUCT",
            }
        )

    return (
        unique,
        duplicates,
    )