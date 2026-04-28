import sqlite3

import pandas as pd

from spendiq.config import CSV_TABLES, DB_PATH


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [
        col.strip().lower().replace(" ", "_")
        for col in df.columns
    ]
    return df


def load_csvs_to_sqlite() -> None:
    conn = sqlite3.connect(DB_PATH)

    try:
        for table_name, csv_path in CSV_TABLES.items():
            if not csv_path.exists():
                raise FileNotFoundError(f"Missing file: {csv_path}")

            df = pd.read_csv(csv_path)
            df = normalize_column_names(df)

            df.to_sql(
                table_name,
                conn,
                if_exists="replace",
                index=False,
            )

            print(f"Loaded {table_name}: {len(df)} rows")

        conn.commit()
        print(f"\nDatabase created at: {DB_PATH}")

    finally:
        conn.close()


def verify_loaded_tables() -> None:
    conn = sqlite3.connect(DB_PATH)

    try:
        cursor = conn.cursor()

        print("\nTable row counts:")
        for table_name in CSV_TABLES.keys():
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            count = cursor.fetchone()[0]
            print(f"- {table_name}: {count}")

    finally:
        conn.close()


def main() -> None:
    load_csvs_to_sqlite()
    verify_loaded_tables()


if __name__ == "__main__":
    main()