from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
DOCS_DIR = BASE_DIR / "docs"

DB_PATH = BASE_DIR / "spendiq.db"

REFERENCE_DATE = "2026-04-21"

CSV_TABLES = {
    "departments": DATA_DIR / "departments.csv",
    "vendors": DATA_DIR / "vendors.csv",
    "contracts": DATA_DIR / "contracts.csv",
    "purchase_orders": DATA_DIR / "purchase_orders.csv",
    "invoices": DATA_DIR / "invoices.csv",
}