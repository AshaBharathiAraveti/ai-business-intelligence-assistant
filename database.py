
import sqlite3
from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "sales.csv"
DB_PATH = BASE_DIR / "sales.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS sales (
                transaction_id TEXT PRIMARY KEY,
                order_date TEXT,
                product TEXT NOT NULL,
                category TEXT,
                region TEXT,
                sales_channel TEXT,
                quantity INTEGER,
                unit_price REAL,
                discount_amount REAL,
                status TEXT
            )
        """)


def import_sales_data():
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"CSV file not found: {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)

    # Normalize column names for the database.
    df.columns = [column.strip() for column in df.columns]

    required_columns = [
        "Transaction_Id", "Order_date", "Product", "Category",
        "Region", "Sales_channel", "Quantity", "Unit_price",
        "Discount_amount", "Status"
    ]

    missing_columns = set(required_columns) - set(df.columns)
    if missing_columns:
        raise ValueError(f"Missing CSV columns: {sorted(missing_columns)}")

    # Remove accidental spaces from text fields.
    text_columns = [
        "Transaction_Id", "Order_date", "Product", "Category",
        "Region", "Sales_channel", "Status"
    ]
    for column in text_columns:
        df[column] = df[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )

    # Convert numeric columns; invalid values become missing.
    for column in ["Quantity", "Unit_price", "Discount_amount"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    # Normalize dates from DD-MM-YYYY to YYYY-MM-DD.
    df["Order_date"] = pd.to_datetime(
        df["Order_date"], format="%d-%m-%Y", errors="coerce"
    ).dt.strftime("%Y-%m-%d")

    # Identify quality issues before importing.
    missing_price_count = int(df["Unit_price"].isna().sum())
    invalid_quantity_count = int(
        (df["Quantity"].isna() | (df["Quantity"] < 0)).sum()
    )
    zero_quantity_count = int((df["Quantity"] == 0).sum())
    invalid_date_count = int(df["Order_date"].isna().sum())
    duplicate_id_count = int(df["Transaction_Id"].duplicated().sum())

    # Keep records with usable identifiers and essential fields.
    valid = df.dropna(
        subset=["Transaction_Id", "Product", "Order_date"]
    ).copy()
    valid = valid.drop_duplicates(subset=["Transaction_Id"], keep="first")

    # Preserve missing prices as NULL. Invalid quantities become NULL.
    valid.loc[
        valid["Quantity"].isna() | (valid["Quantity"] < 0), "Quantity"
    ] = None

    valid.loc[
        valid["Unit_price"] < 0, "Unit_price"
    ] = None

    valid.loc[
        valid["Discount_amount"].isna() |
        (valid["Discount_amount"] < 0), "Discount_amount"
    ] = 0

    records = []
    for _, row in valid.iterrows():
        quantity = row["Quantity"]
        records.append((
            row["Transaction_Id"],
            row["Order_date"],
            row["Product"],
            row["Category"],
            row["Region"],
            row["Sales_channel"],
            int(quantity) if pd.notna(quantity) else None,
            float(row["Unit_price"]) if pd.notna(row["Unit_price"]) else None,
            float(row["Discount_amount"]),
            row["Status"]
        ))

    with get_connection() as connection:
        connection.execute("DELETE FROM sales")
        connection.executemany("""
            INSERT INTO sales (
                transaction_id, order_date, product, category,
                region, sales_channel, quantity, unit_price,
                discount_amount, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, records)

    print(f"CSV rows read: {len(df)}")
    print(f"Rows imported: {len(records)}")
    print(f"Missing unit prices: {missing_price_count}")
    print(f"Invalid quantities: {invalid_quantity_count}")
    print(f"Zero quantities: {zero_quantity_count}")
    print(f"Invalid dates: {invalid_date_count}")
    print(f"Duplicate transaction IDs: {duplicate_id_count}")


if __name__ == "__main__":
    initialize_database()
    import_sales_data()

    with get_connection() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM sales"
        ).fetchone()[0]

    print(f"Database ready: {DB_PATH}")
    print(f"Total records in database: {count}")
