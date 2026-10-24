
from database import get_connection


# Revenue policy:
# - Include only Completed transactions.
# - Exclude rows with missing prices or quantities.
# - Zero quantity contributes zero revenue.
# - Revenue = quantity * unit_price - discount_amount.


def total_revenue():
    query = """
        SELECT
            ROUND(SUM(quantity * unit_price - discount_amount), 2)
                AS total_revenue,
            COUNT(*) AS transaction_count
        FROM sales
        WHERE status = 'Completed'
          AND quantity IS NOT NULL
          AND unit_price IS NOT NULL
    """

    with get_connection() as connection:
        row = connection.execute(query).fetchone()

    return {
        "total_revenue": row["total_revenue"] or 0,
        "transaction_count": row["transaction_count"]
    }


def highest_revenue_product():
    query = """
        SELECT
            product,
            ROUND(SUM(quantity * unit_price - discount_amount), 2)
                AS revenue
        FROM sales
        WHERE status = 'Completed'
          AND quantity IS NOT NULL
          AND unit_price IS NOT NULL
        GROUP BY product
        ORDER BY revenue DESC
        LIMIT 1
    """

    with get_connection() as connection:
        row = connection.execute(query).fetchone()

    return dict(row) if row else None


def revenue_by_region():
    query = """
        SELECT
            region,
            ROUND(SUM(quantity * unit_price - discount_amount), 2)
                AS revenue
        FROM sales
        WHERE status = 'Completed'
          AND quantity IS NOT NULL
          AND unit_price IS NOT NULL
        GROUP BY region
        ORDER BY revenue DESC
    """

    with get_connection() as connection:
        rows = connection.execute(query).fetchall()

    return [dict(row) for row in rows]


def monthly_revenue():
    query = """
        SELECT
            substr(order_date, 1, 7) AS month,
            ROUND(SUM(quantity * unit_price - discount_amount), 2)
                AS revenue
        FROM sales
        WHERE status = 'Completed'
          AND quantity IS NOT NULL
          AND unit_price IS NOT NULL
        GROUP BY substr(order_date, 1, 7)
        ORDER BY month
    """

    with get_connection() as connection:
        rows = connection.execute(query).fetchall()

    return [dict(row) for row in rows]


def data_quality_summary():
    query = """
        SELECT
            COUNT(*) AS total_records,
            SUM(CASE WHEN unit_price IS NULL THEN 1 ELSE 0 END)
                AS missing_prices,
            SUM(CASE WHEN quantity = 0 THEN 1 ELSE 0 END)
                AS zero_quantities,
            SUM(CASE WHEN status = 'Returned' THEN 1 ELSE 0 END)
                AS returned_records
        FROM sales
    """

    with get_connection() as connection:
        row = connection.execute(query).fetchone()

    return dict(row)

def revenue_change_between_months(month_a: str, month_b: str):
    """
    Compare revenue between two months in YYYY-MM format.
    Change = revenue in month_b - revenue in month_a.
    Percentage change is relative to month_a.
    """

    import re

    for month in (month_a, month_b):
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
            raise ValueError("Months must use YYYY-MM format.")

    def get_month_revenue(month):
        query = """
            SELECT
                ROUND(
                    COALESCE(
                        SUM(quantity * unit_price - discount_amount),
                        0
                    ),
                    2
                ) AS revenue
            FROM sales
            WHERE status = 'Completed'
              AND quantity IS NOT NULL
              AND unit_price IS NOT NULL
              AND substr(order_date, 1, 7) = ?
        """

        with get_connection() as connection:
            row = connection.execute(query, (month,)).fetchone()

        return row["revenue"]

    revenue_a = get_month_revenue(month_a)
    revenue_b = get_month_revenue(month_b)

    change = round(revenue_b - revenue_a, 2)

    percentage_change = (
        round((change / revenue_a) * 100, 2)
        if revenue_a != 0
        else None
    )

    return {
        "month_a": month_a,
        "revenue_month_a": revenue_a,
        "month_b": month_b,
        "revenue_month_b": revenue_b,
        "absolute_change": change,
        "percentage_change": percentage_change,
        "interpretation": (
            "increased" if change > 0
            else "decreased" if change < 0
            else "unchanged"
        ),
    }


if __name__ == "__main__":
    print("\n--- Total Revenue ---")
    print(total_revenue())

    print("\n--- Highest Revenue Product ---")
    print(highest_revenue_product())

    print("\n--- Revenue by Region ---")
    print(revenue_by_region())

    print("\n--- Monthly Revenue ---")
    print(monthly_revenue())

    print("\n--- Data Quality ---")
    print(data_quality_summary())
