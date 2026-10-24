
from fastapi.testclient import TestClient

from main import app
from analytics import (
    total_revenue,
    highest_revenue_product,
    revenue_by_region,
    monthly_revenue,
    data_quality_summary,
    revenue_change_between_months,
)

client = TestClient(app)


def test_total_revenue():
    result = total_revenue()
    assert result["total_revenue"] == 1439200.0
    assert result["transaction_count"] == 49


def test_highest_revenue_product():
    result = highest_revenue_product()
    assert result["product"] == "Monitor"
    assert result["revenue"] == 473000.0


def test_revenue_by_region():
    result = revenue_by_region()
    assert len(result) == 4
    assert result[0]["region"] == "South"
    assert result[0]["revenue"] == 411200.0


def test_monthly_revenue():
    result = monthly_revenue()
    assert len(result) == 6
    assert result[0]["month"] == "2026-01"
    assert result[-1]["month"] == "2026-06"


def test_data_quality_summary():
    result = data_quality_summary()
    assert result["total_records"] == 51
    assert result["missing_prices"] == 1
    assert result["zero_quantities"] == 1
    assert result["returned_records"] == 1


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_revenue_change_between_months():
    result = revenue_change_between_months("2026-01", "2026-02")

    assert result["revenue_month_a"] == 210250.0
    assert result["revenue_month_b"] == 234600.0
    assert result["absolute_change"] == 24350.0
    assert result["percentage_change"] == 11.58
    assert result["interpretation"] == "increased"


def test_ask_total_revenue():
    response = client.post(
        "/ask",
        json={"question": "What is the total revenue?"},
    )

    assert response.status_code == 200
    assert response.json()["intent"] == "total_revenue"
    assert response.json()["answer"]["total_revenue"] == 1439200.0


def test_ask_unsupported_question():
    response = client.post(
        "/ask",
        json={"question": "Tell me a joke"},
    )

    assert response.status_code == 422
    assert "not supported" in response.json()["detail"].lower()


def test_revenue_change_invalid_month():
    import pytest

    with pytest.raises(ValueError):
        revenue_change_between_months("2026-13", "2026-02")

