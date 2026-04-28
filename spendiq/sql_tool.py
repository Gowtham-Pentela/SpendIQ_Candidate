from __future__ import annotations

from typing import Any

from spendiq.config import REFERENCE_DATE
from spendiq.db import execute_query


def total_spend_with_vendor_last_12_months(vendor_name: str) -> dict[str, Any]:
    """
    Calculates total invoice spend with a vendor over the 12 months before REFERENCE_DATE.
    Uses invoice_date because invoices represent actual spend.
    """
    sql = """
        SELECT
            v.vendor_name,
            ROUND(SUM(i.amount), 2) AS total_spend,
            COUNT(i.invoice_id) AS invoice_count,
            MIN(i.invoice_date) AS first_invoice_date,
            MAX(i.invoice_date) AS last_invoice_date
        FROM invoices i
        JOIN vendors v
            ON i.vendor_id = v.vendor_id
        WHERE LOWER(v.vendor_name) LIKE LOWER(?)
          AND DATE(i.invoice_date) >= DATE(?, '-12 months')
          AND DATE(i.invoice_date) <= DATE(?)
        GROUP BY v.vendor_name
    """

    rows = execute_query(
        sql,
        (f"%{vendor_name}%", REFERENCE_DATE, REFERENCE_DATE),
    )

    if not rows:
        return {
            "answer": f"No invoice spend found for vendor matching '{vendor_name}' in the last 12 months.",
            "rows": [],
            "sources": ["invoices", "vendors"],
        }

    row = rows[0]
    return {
        "answer": (
            f"Total spend with {row['vendor_name']} over the last 12 months "
            f"was ${row['total_spend']:,.2f} across {row['invoice_count']} invoices."
        ),
        "rows": rows,
        "sources": ["invoices", "vendors"],
    }


def top_vendors_by_ytd_spend(limit: int = 10) -> dict[str, Any]:
    """
    Calculates top vendors by invoice spend from Jan 1 of the reference year to REFERENCE_DATE.
    """
    sql = """
        SELECT
            v.vendor_name,
            v.category,
            ROUND(SUM(i.amount), 2) AS ytd_spend,
            COUNT(i.invoice_id) AS invoice_count
        FROM invoices i
        JOIN vendors v
            ON i.vendor_id = v.vendor_id
        WHERE DATE(i.invoice_date) >= DATE(?, 'start of year')
          AND DATE(i.invoice_date) <= DATE(?)
        GROUP BY v.vendor_id, v.vendor_name, v.category
        ORDER BY ytd_spend DESC
        LIMIT ?
    """

    rows = execute_query(sql, (REFERENCE_DATE, REFERENCE_DATE, limit))

    return {
        "answer": f"Top {limit} vendors by year-to-date spend as of {REFERENCE_DATE}.",
        "rows": rows,
        "sources": ["invoices", "vendors"],
    }


def active_contracts_by_category() -> dict[str, Any]:
    """
    Counts active contracts grouped by vendor category.
    """
    sql = """
        SELECT
            v.category,
            COUNT(c.contract_id) AS active_contract_count
        FROM contracts c
        JOIN vendors v
            ON c.vendor_id = v.vendor_id
        WHERE c.status = 'Active'
        GROUP BY v.category
        ORDER BY active_contract_count DESC, v.category
    """

    rows = execute_query(sql)

    return {
        "answer": "Active contracts broken down by vendor category.",
        "rows": rows,
        "sources": ["contracts", "vendors"],
    }


def auto_renew_contracts_expiring_next_90_days() -> dict[str, Any]:
    """
    Finds active auto-renewing contracts ending within 90 days of REFERENCE_DATE.
    """
    sql = """
        SELECT
            c.contract_id,
            c.contract_name,
            v.vendor_name,
            c.end_date,
            c.notice_period_days,
            c.document_path
        FROM contracts c
        JOIN vendors v
            ON c.vendor_id = v.vendor_id
        WHERE c.status = 'Active'
          AND c.auto_renew = 1
          AND DATE(c.end_date) BETWEEN DATE(?) AND DATE(?, '+90 days')
        ORDER BY DATE(c.end_date)
    """

    rows = execute_query(sql, (REFERENCE_DATE, REFERENCE_DATE))

    return {
        "answer": f"Auto-renewing active contracts expiring in the next 90 days from {REFERENCE_DATE}.",
        "rows": rows,
        "sources": ["contracts", "vendors"],
    }


def vendors_with_ytd_spend_over_50k_no_active_contract() -> dict[str, Any]:
    """
    Finds vendors with YTD invoice spend over $50K and no active contract.
    """
    sql = """
        WITH ytd_spend AS (
            SELECT
                i.vendor_id,
                SUM(i.amount) AS ytd_spend,
                COUNT(i.invoice_id) AS invoice_count
            FROM invoices i
            WHERE DATE(i.invoice_date) >= DATE(?, 'start of year')
              AND DATE(i.invoice_date) <= DATE(?)
            GROUP BY i.vendor_id
        ),
        active_contracts AS (
            SELECT DISTINCT vendor_id
            FROM contracts
            WHERE status = 'Active'
        )
        SELECT
            v.vendor_id,
            v.vendor_name,
            v.category,
            ROUND(y.ytd_spend, 2) AS ytd_spend,
            y.invoice_count
        FROM ytd_spend y
        JOIN vendors v
            ON y.vendor_id = v.vendor_id
        LEFT JOIN active_contracts ac
            ON y.vendor_id = ac.vendor_id
        WHERE y.ytd_spend > 50000
          AND ac.vendor_id IS NULL
        ORDER BY y.ytd_spend DESC
    """

    rows = execute_query(sql, (REFERENCE_DATE, REFERENCE_DATE))

    return {
        "answer": "Vendors with more than $50,000 in YTD invoice spend but no active contract.",
        "rows": rows,
        "sources": ["invoices", "vendors", "contracts"],
    }


def invoices_with_terms_shorter_than_contract() -> dict[str, Any]:
    """
    Finds invoices where billed payment terms are shorter than the underlying contract terms.
    Invoice terms shorter than contract terms can indicate unfavorable payment behavior.
    """
    sql = """
        SELECT
            i.invoice_id,
            v.vendor_name,
            i.invoice_date,
            i.amount,
            i.payment_terms_days AS invoice_payment_terms_days,
            c.payment_terms_days AS contract_payment_terms_days,
            c.contract_id,
            c.contract_name,
            c.document_path
        FROM invoices i
        JOIN purchase_orders po
            ON i.po_id = po.po_id
        JOIN contracts c
            ON po.contract_id = c.contract_id
        JOIN vendors v
            ON i.vendor_id = v.vendor_id
        WHERE po.contract_id IS NOT NULL
          AND po.contract_id != ''
          AND i.payment_terms_days < c.payment_terms_days
        ORDER BY i.invoice_date DESC
        LIMIT 25
    """

    rows = execute_query(sql)

    return {
        "answer": "Invoices where billed payment terms are shorter than the underlying contract terms.",
        "rows": rows,
        "sources": ["invoices", "purchase_orders", "contracts", "vendors"],
    }


def contracts_where_invoice_spend_exceeds_cap() -> dict[str, Any]:
    """
    Finds contracts where cumulative invoice spend exceeds contract total value cap.
    """
    sql = """
        SELECT
            c.contract_id,
            c.contract_name,
            v.vendor_name,
            c.total_value_cap_usd,
            ROUND(SUM(i.amount), 2) AS cumulative_invoice_spend,
            ROUND(SUM(i.amount) - c.total_value_cap_usd, 2) AS amount_over_cap,
            COUNT(i.invoice_id) AS invoice_count,
            c.document_path
        FROM contracts c
        JOIN vendors v
            ON c.vendor_id = v.vendor_id
        JOIN purchase_orders po
            ON c.contract_id = po.contract_id
        JOIN invoices i
            ON po.po_id = i.po_id
        WHERE c.total_value_cap_usd IS NOT NULL
        GROUP BY
            c.contract_id,
            c.contract_name,
            v.vendor_name,
            c.total_value_cap_usd,
            c.document_path
        HAVING SUM(i.amount) > c.total_value_cap_usd
        ORDER BY amount_over_cap DESC
    """

    rows = execute_query(sql)

    return {
        "answer": "Contracts where cumulative invoice spend exceeds the stated total contract value cap.",
        "rows": rows,
        "sources": ["contracts", "purchase_orders", "invoices", "vendors"],
    }


def run_sql_tool(question: str) -> dict[str, Any]:
    """
    Simple deterministic router for structured-data questions.

    This is intentionally simple for the prototype. In production, this could be replaced
    with an LLM router or a tool-calling framework, but deterministic routing is easier
    to debug and demo under time constraints.
    """
    q = question.lower()

    if "stratos" in q and ("spend" in q or "total" in q):
        return total_spend_with_vendor_last_12_months("Stratos Cloud Services")

    if "top" in q and "vendor" in q and ("ytd" in q or "year-to-date" in q or "spend" in q):
        return top_vendors_by_ytd_spend()

    if "active contract" in q and ("category" in q or "broken down" in q):
        return active_contracts_by_category()

    if "auto-renew" in q or "auto renew" in q:
        if "90" in q or "next" in q or "expiring" in q:
            return auto_renew_contracts_expiring_next_90_days()

    if "no active contract" in q or "without active contract" in q:
        return vendors_with_ytd_spend_over_50k_no_active_contract()

    if "payment terms" in q and ("shorter" in q or "contract" in q):
        return invoices_with_terms_shorter_than_contract()

    if "exceeded" in q or "exceeds" in q or "cap" in q:
        return contracts_where_invoice_spend_exceeds_cap()

    return {
        "answer": (
            "I could not confidently map this to a supported structured-data query yet. "
            "Try asking about top vendors, vendor spend, active contracts, payment terms, "
            "auto-renewals, vendors without active contracts, or contract cap overages."
        ),
        "rows": [],
        "sources": [],
    }