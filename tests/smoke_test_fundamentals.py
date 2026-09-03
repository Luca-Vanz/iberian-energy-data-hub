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
    assert client.get("/fundamentals/generation?country=FR").status_code == 422
    print("Fundamentals smoke test passed.")


if __name__ == "__main__":
    main()
