from __future__ import annotations

import argparse
import hashlib
import json
import zipfile

from pathlib import Path


TEXT_SUFFIXES = {
    ".csv",
    ".dat",
    ".txt",
}

DELIMITER_CANDIDATES = [
    ";",
    ",",
    "\t",
    "|",
]


def sha256_file(
    path: Path,
) -> str:

    digest = hashlib.sha256()

    with path.open("rb") as handle:

        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):

            digest.update(chunk)

    return digest.hexdigest()


def decode_sample(
    data: bytes,
) -> tuple[str | None, str | None]:

    if b"\x00" in data:

        return None, None

    for encoding in [
        "utf-8-sig",
        "cp1252",
        "latin-1",
    ]:

        try:

            return data.decode(encoding), encoding

        except UnicodeDecodeError:

            continue

    return None, None


def delimiter_hint(
    lines: list[str],
) -> str | None:

    non_empty = [
        line
        for line in lines
        if line.strip()
    ]

    if not non_empty:

        return None

    scores = {
        delimiter: sum(
            line.count(delimiter)
            for line in non_empty[:10]
        )
        for delimiter in DELIMITER_CANDIDATES
    }

    delimiter = max(
        scores,
        key=scores.get,
    )

    if scores[delimiter] == 0:

        return None

    return delimiter


def inspect_bytes(
    data: bytes,
    suffix: str,
    sample_lines: int,
) -> dict:

    if suffix.lower() not in TEXT_SUFFIXES:

        return {
            "text_sample": None,
            "encoding_hint": None,
            "delimiter_hint": None,
        }

    text, encoding = decode_sample(data)

    if text is None:

        return {
            "text_sample": None,
            "encoding_hint": None,
            "delimiter_hint": None,
        }

    lines = text.splitlines()

    return {
        "text_sample": lines[:sample_lines],
        "encoding_hint": encoding,
        "delimiter_hint": delimiter_hint(lines),
    }


def inspect_regular_file(
    path: Path,
    sample_lines: int,
    max_sample_bytes: int,
) -> dict:

    with path.open("rb") as handle:

        sample = handle.read(max_sample_bytes)

    return {
        "package_type": "file",
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        **inspect_bytes(
            sample,
            path.suffix,
            sample_lines,
        ),
    }


def inspect_zip_file(
    path: Path,
    sample_lines: int,
    max_sample_bytes: int,
) -> dict:

    members = []

    with zipfile.ZipFile(path) as archive:

        for info in archive.infolist():

            if info.is_dir():

                continue

            member_path = Path(info.filename)

            with archive.open(info) as handle:

                sample = handle.read(max_sample_bytes)

            members.append(
                {
                    "name": info.filename,
                    "basename": member_path.name,
                    "size_bytes": info.file_size,
                    "compressed_size_bytes": info.compress_size,
                    "crc32": f"{info.CRC:08x}",
                    **inspect_bytes(
                        sample,
                        member_path.suffix,
                        sample_lines,
                    ),
                }
            )

    return {
        "package_type": "zip",
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "member_count": len(members),
        "members": members,
    }


def inspect_package(
    path: Path,
    sample_lines: int = 5,
    max_sample_bytes: int = 65536,
) -> dict:

    path = path.resolve()

    if not path.is_file():

        raise FileNotFoundError(
            f"Historical package not found: {path}"
        )

    if sample_lines < 0:

        raise ValueError(
            "sample_lines must be zero or greater."
        )

    if max_sample_bytes < 1:

        raise ValueError(
            "max_sample_bytes must be greater than zero."
        )

    if zipfile.is_zipfile(path):

        return inspect_zip_file(
            path,
            sample_lines,
            max_sample_bytes,
        )

    return inspect_regular_file(
        path,
        sample_lines,
        max_sample_bytes,
    )


def main() -> None:

    parser = argparse.ArgumentParser(
        description=(
            "Inspect an unknown historical OMIE package without "
            "extracting, transforming or loading its contents."
        )
    )

    parser.add_argument(
        "package",
        type=Path,
        help="Path to an OMIE file or ZIP package.",
    )

    parser.add_argument(
        "--sample-lines",
        type=int,
        default=5,
        help="Maximum sample lines shown for each text file.",
    )

    parser.add_argument(
        "--max-sample-bytes",
        type=int,
        default=65536,
        help="Maximum bytes read for format inspection per file.",
    )

    args = parser.parse_args()

    report = inspect_package(
        args.package,
        sample_lines=args.sample_lines,
        max_sample_bytes=args.max_sample_bytes,
    )

    print(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":

    main()
