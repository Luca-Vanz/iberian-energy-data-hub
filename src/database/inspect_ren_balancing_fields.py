import xml.etree.ElementTree as ET
from pathlib import Path


BASE_DIR = (
    Path("data")
    / "raw"
    / "ren"
    / "balancing"
)


SERIES = [
    "afrr_energy",
    "afrr_capacity",
    "mfrr_legacy_regulating_reserve",
    "mfrr",
    "rr_legacy",
    "rr",
]


def local_name(tag: str) -> str:

    return (
        tag
        .split("}")[-1]
        .upper()
    )


def find_first_item(root):

    for element in root.iter():

        if (
            local_name(element.tag)
            == "ITEM"
        ):

            return element

    return None


def main():

    print("=" * 90)
    print(
        "REN BALANCING XML FIELD INSPECTION"
    )
    print("=" * 90)

    for series in SERIES:

        directory = (
            BASE_DIR
            / series
        )

        files = sorted(
            directory.glob("*.xml")
        )

        print()
        print(
            f"{series}"
        )

        if not files:

            print(
                "  NO FILES FOUND"
            )
            continue

        path = files[0]

        print(
            f"  File: "
            f"{path.name}"
        )

        root = ET.fromstring(
            path.read_text(
                encoding="utf-8"
            )
        )

        item = find_first_item(
            root
        )

        if item is None:

            print(
                "  NO ITEM FOUND"
            )
            continue

        print(
            "  First observation:"
        )

        for child in item:

            name = local_name(
                child.tag
            )

            value = (
                child.text.strip()
                if child.text
                else None
            )

            print(
                f"    {name}: "
                f"{value}"
            )

    print()
    print("=" * 90)


if __name__ == "__main__":
    main()