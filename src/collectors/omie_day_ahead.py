import argparse
from pathlib import Path

import requests


BASE_URL = "https://www.omie.es/en/file-download"
FILE_PREFIX = "marginalpdbc"

MAX_REVISION = 9


def find_existing_raw_file(
    date: str,
) -> Path | None:

    output_dir = (
        Path("data")
        / "raw"
        / "omie"
    )

    matching_files = list(
        output_dir.glob(
            f"{FILE_PREFIX}_{date}.*"
        )
    )

    valid_files = []

    for path in matching_files:

        try:
            revision = int(path.suffix[1:])
        except ValueError:
            continue

        valid_files.append(
            (revision, path)
        )


    if not valid_files:
        return None


    valid_files.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    return valid_files[0][1]


def download_omie_day_ahead(
    date: str,
    force: bool = False,
) -> Path:

    output_dir = (
        Path("data")
        / "raw"
        / "omie"
    )

    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    existing_file = find_existing_raw_file(
        date
    )


    if (
        existing_file is not None
        and not force
    ):

        print(
            "Raw file already exists, "
            f"skipping download: {existing_file}"
        )

        return existing_file


    for revision in range(
        1,
        MAX_REVISION + 1,
    ):

        filename = (
            f"{FILE_PREFIX}_{date}.{revision}"
        )

        params = {
            "filename": filename,
            "parents": FILE_PREFIX,
        }


        response = requests.get(
            BASE_URL,
            params=params,
            timeout=30,
        )


        if response.status_code == 404:

            print(
                f"{filename} not found, "
                "trying next revision..."
            )

            continue


        response.raise_for_status()


        output_path = (
            output_dir
            / filename
        )


        output_path.write_bytes(
            response.content
        )


        print(
            f"Downloaded {len(response.content)} bytes "
            f"to {output_path}"
        )


        return output_path


    raise FileNotFoundError(
        f"No OMIE file found for {date} "
        f"after checking revisions "
        f"1 to {MAX_REVISION}."
    )


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Download OMIE day-ahead "
            "electricity prices."
        )
    )


    parser.add_argument(
        "date",
        help="Market date in YYYYMMDD format.",
    )


    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Download the file again "
            "even if it already exists."
        ),
    )


    args = parser.parse_args()


    download_omie_day_ahead(
        date=args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()