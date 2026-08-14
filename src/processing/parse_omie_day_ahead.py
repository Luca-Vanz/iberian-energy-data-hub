from pathlib import Path

import pandas as pd


DATE = "20260813"

raw_path = Path("data") / "raw" / "omie" / f"marginalpdbc_{DATE}.1"

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
        "price_pt_eur_mwh",
        "price_es_eur_mwh",
    ],
    engine="python",
)

df["date"] = pd.to_datetime(
    df[["year", "month", "day"]]
)

# Check for missing values
if df.isnull().any().any():
    raise ValueError("Missing values found in OMIE data")

# Check for duplicate periods
if df["period"].duplicated().any():
    raise ValueError("Duplicate periods found")

# Check that periods are sequential
expected_periods = list(range(1, len(df) + 1))
actual_periods = df["period"].tolist()

if actual_periods != expected_periods:
    raise ValueError("Periods are not sequential")

# A normal day has 96 periods.
# DST transition days can have 92 or 100.
valid_period_counts = {92, 96, 100}

if len(df) not in valid_period_counts:
    raise ValueError(
        f"Unexpected number of periods: {len(df)}"
    )

# Create timezone-aware 15-minute timestamps
market_date = df["date"].iloc[0]
next_date = market_date + pd.Timedelta(days=1)

timestamps = pd.date_range(
    start=market_date,
    end=next_date,
    freq="15min",
    inclusive="left",
    tz="Europe/Madrid",
)

# Check that the number of timestamps matches the number of OMIE periods
if len(timestamps) != len(df):
    raise ValueError(
        f"Timestamp count ({len(timestamps)}) "
        f"does not match OMIE period count ({len(df)})"
    )

# Add local market time and UTC time
df["timestamp_market"] = timestamps
df["timestamp_utc"] = df["timestamp_market"].dt.tz_convert("UTC")


# Create the clean processed dataset
processed_df = df[
    [
        "timestamp_utc",
        "timestamp_market",
        "period",
        "price_es_eur_mwh",
        "price_pt_eur_mwh",
    ]
].copy()


# Create processed-data folder if it does not exist
processed_dir = Path("data") / "processed" / "omie"
processed_dir.mkdir(parents=True, exist_ok=True)

# Define output file
output_path = processed_dir / f"day_ahead_prices_{DATE}.csv"

# Save processed dataframe
processed_df.to_csv(
    output_path,
    index=False,
)


# Print results
print("Validation passed!")
print()
print(processed_df.head())
print()
print(processed_df.tail())
print()
print(f"Processed data saved to: {output_path}")