from fastapi import FastAPI

from src.analytics.omie import get_daily_market_summary


app = FastAPI(
    title="Iberian Energy Data Hub API",
    description="API for Iberian electricity market data and analytics.",
    version="0.1.0",
)


@app.get("/")
def root():
    return {
        "message": "Iberian Energy Data Hub API"
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok"
    }


@app.get("/omie/daily-summary")
def omie_daily_summary():
    df = get_daily_market_summary()

    return df.to_dict(
        orient="records"
    )