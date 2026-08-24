import tempfile
import unittest
import zipfile

from pathlib import Path

from src.processing.inspect_omie_historical_package import (
    inspect_package,
)


class InspectHistoricalOmiePackageTests(
    unittest.TestCase,
):

    def test_regular_semicolon_file(self) -> None:

        with tempfile.TemporaryDirectory() as directory:

            path = Path(directory) / "historical.dat"

            path.write_text(
                "year;month;day;period;price\n"
                "2007;7;1;1;42.50\n",
                encoding="utf-8",
            )

            report = inspect_package(path)

            self.assertEqual(
                report["package_type"],
                "file",
            )

            self.assertEqual(
                report["delimiter_hint"],
                ";",
            )

            self.assertEqual(
                report["encoding_hint"],
                "utf-8-sig",
            )

            self.assertEqual(
                len(report["sha256"]),
                64,
            )

    def test_zip_is_inspected_without_extraction(self) -> None:

        with tempfile.TemporaryDirectory() as directory:

            root = Path(directory)
            path = root / "historical.zip"

            with zipfile.ZipFile(
                path,
                "w",
            ) as archive:

                archive.writestr(
                    "nested/prices.csv",
                    "date,period,price\n2007-07-01,1,42.50\n",
                )

                archive.writestr(
                    "documentation/readme.txt",
                    "Official OMIE historical package\n",
                )

            report = inspect_package(
                path,
                sample_lines=1,
            )

            self.assertEqual(
                report["package_type"],
                "zip",
            )

            self.assertEqual(
                report["member_count"],
                2,
            )

            self.assertEqual(
                report["members"][0]["delimiter_hint"],
                ",",
            )

            self.assertEqual(
                len(report["members"][0]["text_sample"]),
                1,
            )

            self.assertFalse(
                (root / "nested").exists()
            )

    def test_missing_package_is_rejected(self) -> None:

        with self.assertRaises(FileNotFoundError):

            inspect_package(
                Path("does-not-exist.zip")
            )


if __name__ == "__main__":

    unittest.main()
