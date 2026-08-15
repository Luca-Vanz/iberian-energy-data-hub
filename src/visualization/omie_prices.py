from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.analytics.omie import get_daily_market_summary


OUTPUT_PATH = (
    Path("data")
    / "processed"
    / "omie"
    / "daily_average_prices.png"
)


def plot_daily_prices():
    df = get_daily_market_summary()

    # Convert YYYYMMDD text into real dates
    df["market_date"] = pd.to_datetime(
        df["market_date"],
        format="%Y%m%d",
    )

    plt.figure(figsize=(10, 5))

    plt.plot(
        df["market_date"],
        df["avg_price_es"],
        marker="o",
        label="Spain",
    )

    plt.plot(
        df["market_date"],
        df["avg_price_pt"],
        marker="o",
        label="Portugal",
    )

    plt.xlabel("Market date")
    plt.ylabel("Day-ahead price (€/MWh)")
    plt.title("OMIE Daily Average Day-Ahead Prices")

    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    plt.savefig(
        OUTPUT_PATH,
        dpi=150,
        bbox_inches="tight",
    )

    print(f"Chart saved to: {OUTPUT_PATH}")

    plt.show()


if __name__ == "__main__":
    plot_daily_prices()