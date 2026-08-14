import argparse
from pathlib import Path

import requests


BASE_URL = "https://www.omie.es/en/file-download"
FILE_PREFIX = "marginalpdbc"


def download_omie_day_ahead(date: str, force: bool = False) -> Path:
    filename = f"{FILE_PREFIX}_{date}.1"

    output_dir = Path("data") / "raw" / "omie"
    output_dir.mkdir(parents=True, exist_ok=True)

    output_path = output_dir / filename

    # Do not download again if the raw file already exists
    if output_path.exists() and not force:
        print(f"Raw file already exists, skipping download: {output_path}")
        return output_path

    params = {
        "filename": filename,
        "parents": FILE_PREFIX,
    }

    response = requests.get(
        BASE_URL,
        params=params,
        timeout=30,
    )

    response.raise_for_status()

    output_path.write_bytes(response.content)

    print(f"Downloaded {len(response.content)} bytes")
    print(f"Saved to: {output_path}")

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description="Download OMIE day-ahead electricity prices."
    )

    parser.add_argument(
        "date",
        help="Market date in YYYYMMDD format, for example 20260813",
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help="Download the file again even if it already exists.",
    )

    args = parser.parse_args()

    download_omie_day_ahead(
        args.date,
        force=args.force,
    )


if __name__ == "__main__":
    main()