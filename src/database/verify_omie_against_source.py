from pathlib import Path
import sqlite3

import pandas as pd


RAW_DIR = (
    Path("data")
    / "raw"
    / "omie"
)

PUBLIC_DATABASE_PATH = (
    Path("deployment")
    / "iberian_energy_public.db"
)


START_DATE = "20251001"
END_DATE = "20260814"


def find_raw_file(
    date: str,
) -> Path:

    files = list(
        RAW_DIR.glob(
            f"marginalpdbc_{date}.*"
        )
    )


    if not files:

        raise FileNotFoundError(
            f"No raw OMIE file found "
            f"for {date}."
        )


    revisions = []


    for file in files:

        try:
            revision = int(
                file.suffix[1:]
            )

        except ValueError:
            continue


        revisions.append(
            (
                revision,
                file,
            )
        )


    if not revisions:

        raise FileNotFoundError(
            f"No valid OMIE revision "
            f"found for {date}."
        )


    revisions.sort(
        key=lambda item:
            item[0]
    )


    return revisions[-1][1]


def read_original_omie(
    date: str,
) -> pd.DataFrame:

    raw_path = find_raw_file(
        date
    )


    df = pd.read_csv(
        raw_path,
        sep=";",
        skiprows=1,
        skipfooter=1,
        header=None,
        usecols=range(6),
        names=[
            "year",
            "month",
            "day",
            "period",
            "price_pt",
            "price_es",
        ],
        engine="python",
    )


    if df.isnull().any().any():

        raise ValueError(
            f"Null values found in "
            f"original OMIE file "
            f"for {date}."
        )


    expected_periods = list(
        range(
            1,
            len(df) + 1,
        )
    )


    actual_periods = (
        df["period"]
        .astype(int)
        .tolist()
    )


    if (
        actual_periods
        != expected_periods
    ):

        raise ValueError(
            f"Invalid period sequence "
            f"in original OMIE file "
            f"for {date}."
        )


    market_date = pd.to_datetime(
        date,
        format="%Y%m%d",
    )


    next_date = (
        market_date
        + pd.Timedelta(days=1)
    )


    timestamps_market = (
        pd.date_range(
            start=market_date,
            end=next_date,
            freq="15min",
            inclusive="left",
            tz="Europe/Madrid",
        )
    )


    if (
        len(timestamps_market)
        != len(df)
    ):

        raise ValueError(
            f"Timestamp count mismatch "
            f"for {date}: "
            f"{len(df)} source periods, "
            f"{len(timestamps_market)} "
            f"expected timestamps."
        )


    df["timestamp_market"] = (
        timestamps_market
    )


    df["timestamp_utc"] = (
        timestamps_market
        .tz_convert("UTC")
    )


    return df


def verify_database():

    if not PUBLIC_DATABASE_PATH.exists():

        raise FileNotFoundError(
            f"Public database not found: "
            f"{PUBLIC_DATABASE_PATH}"
        )


    with sqlite3.connect(
        PUBLIC_DATABASE_PATH
    ) as connection:

        database = pd.read_sql_query(
            """
            SELECT
                timestamp_utc,
                timestamp_market,
                market_date,
                period,
                bidding_zone,
                price_eur_mwh

            FROM omie_day_ahead_prices

            WHERE market_date
                BETWEEN ? AND ?

            ORDER BY
                market_date,
                period,
                bidding_zone;
            """,
            connection,
            params=[
                START_DATE,
                END_DATE,
            ],
        )


    database[
        "market_date"
    ] = (
        database[
            "market_date"
        ]
        .astype(str)
    )


    database[
        "period"
    ] = (
        database[
            "period"
        ]
        .astype(int)
    )


    database[
        "price_eur_mwh"
    ] = pd.to_numeric(
        database[
            "price_eur_mwh"
        ],
        errors="raise",
    )


    database_dates = sorted(
        database[
            "market_date"
        ]
        .unique()
    )


    total_source_periods = 0

    total_compared_prices = 0

    price_mismatches = []

    timestamp_mismatches = []

    missing_database_rows = []


    print("=" * 65)

    print(
        "OMIE ORIGINAL SOURCE VS PUBLIC DATABASE"
    )

    print("=" * 65)

    print()

    print(
        f"Dates in public database: "
        f"{len(database_dates)}"
    )

    print()


    for index, date in enumerate(
        database_dates,
        start=1,
    ):

        source = read_original_omie(
            date
        )


        total_source_periods += (
            len(source)
        )


        database_day = (
            database[
                database[
                    "market_date"
                ] == date
            ]
        )


        expected_database_rows = (
            len(source) * 2
        )


        if (
            len(database_day)
            != expected_database_rows
        ):

            missing_database_rows.append(
                (
                    date,
                    len(database_day),
                    expected_database_rows,
                )
            )


        for source_row in (
            source.itertuples(
                index=False
            )
        ):

            period = int(
                source_row.period
            )


            expected_timestamp_utc = str(
                source_row.timestamp_utc
            )


            expected_timestamp_market = str(
                source_row.timestamp_market
            )


            for (
                zone,
                source_price,
            ) in [
                (
                    "ES",
                    source_row.price_es,
                ),
                (
                    "PT",
                    source_row.price_pt,
                ),
            ]:

                match = database_day[
                    (
                        database_day[
                            "period"
                        ] == period
                    )
                    &
                    (
                        database_day[
                            "bidding_zone"
                        ] == zone
                    )
                ]


                if len(match) != 1:

                    missing_database_rows.append(
                        (
                            date,
                            period,
                            zone,
                            len(match),
                        )
                    )

                    continue


                database_row = (
                    match.iloc[0]
                )


                database_price = float(
                    database_row[
                        "price_eur_mwh"
                    ]
                )


                source_price = float(
                    source_price
                )


                total_compared_prices += 1


                if (
                    abs(
                        database_price
                        - source_price
                    )
                    > 0.000001
                ):

                    price_mismatches.append(
                        {
                            "date": date,
                            "period": period,
                            "zone": zone,
                            "source_price":
                                source_price,
                            "database_price":
                                database_price,
                        }
                    )


                if (
                    database_row[
                        "timestamp_utc"
                    ]
                    != expected_timestamp_utc
                    or
                    database_row[
                        "timestamp_market"
                    ]
                    != expected_timestamp_market
                ):

                    timestamp_mismatches.append(
                        {
                            "date": date,
                            "period": period,
                            "zone": zone,
                        }
                    )


        print(
            f"[{index}/{len(database_dates)}] "
            f"{date}: "
            f"{len(source)} periods checked"
        )


    print()
    print("=" * 65)

    print(
        "VERIFICATION SUMMARY"
    )

    print("=" * 65)


    print(
        f"Market days checked: "
        f"{len(database_dates)}"
    )

    print(
        f"Original OMIE periods checked: "
        f"{total_source_periods}"
    )

    print(
        f"ES/PT prices compared: "
        f"{total_compared_prices}"
    )


    print()

    print(
        f"Price mismatches: "
        f"{len(price_mismatches)}"
    )

    print(
        f"Timestamp mismatches: "
        f"{len(timestamp_mismatches)}"
    )

    print(
        f"Missing / duplicate database rows: "
        f"{len(missing_database_rows)}"
    )


    verification_passed = (
        len(price_mismatches) == 0
        and
        len(timestamp_mismatches) == 0
        and
        len(missing_database_rows) == 0
    )


    print()
    print("=" * 65)


    if verification_passed:

        print(
            "SOURCE VERIFICATION PASSED"
        )

    else:

        print(
            "SOURCE VERIFICATION FAILED"
        )


    print("=" * 65)


    if price_mismatches:

        print()
        print(
            "First price mismatches:"
        )


        for mismatch in (
            price_mismatches[:10]
        ):

            print(
                mismatch
            )


    if timestamp_mismatches:

        print()
        print(
            "First timestamp mismatches:"
        )


        for mismatch in (
            timestamp_mismatches[:10]
        ):

            print(
                mismatch
            )


    if missing_database_rows:

        print()
        print(
            "First missing / duplicate rows:"
        )


        for issue in (
            missing_database_rows[:10]
        ):

            print(
                issue
            )


if __name__ == "__main__":

    verify_database()