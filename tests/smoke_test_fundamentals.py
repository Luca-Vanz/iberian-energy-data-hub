from fastapi.testclient import TestClient

from src.api.main import app


client = TestClient(app)


def check(path: str) -> list[dict]:
    response = client.get(path)
    assert response.status_code == 200, response.text
    rows = response.json()
    assert rows, f"No rows returned by {path}"
    assert {row["source"] for row in rows} == {"ENTSO-E"}
    return rows


def main() -> None:
    for country in ("ES", "PT"):
        generation = check(f"/fundamentals/generation?country={country}")
        capacity = check(f"/fundamentals/installed-capacity?country={country}")
        assert min(row["coverage_ratio"] for row in generation) >= 0
        assert max(row["coverage_ratio"] for row in generation) <= 1
        assert min(row["year"] for row in capacity) == 2018
        assert max(row["year"] for row in capacity) == 2026
        assert min(row["period"] for row in generation) == "2018-01-01"
        annual = check(
            f"/fundamentals/generation?country={country}"
            "&start_date=2024-01-01&end_date=2025-12-31&frequency=yearly"
        )
        assert {row["period"] for row in annual} == {"2024", "2025"}
        filtered_capacity = check(
            f"/fundamentals/installed-capacity?country={country}"
            "&start_year=2020&end_year=2022"
        )
        assert {row["year"] for row in filtered_capacity} == {2020, 2021, 2022}
    assert client.get("/fundamentals/generation?country=FR").status_code == 422
    assert client.get(
        "/fundamentals/generation?country=ES&start_date=2025-01-01&end_date=2024-01-01"
    ).status_code == 422
    assert client.get(
        "/fundamentals/installed-capacity?country=ES&start_year=2025&end_year=2024"
    ).status_code == 422
    print("Fundamentals smoke test passed.")


if __name__ == "__main__":
    main()
