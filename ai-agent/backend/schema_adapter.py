# backend/schema_adapter.py
"""
Centralized Schema Adapter for E-Sahakara AI Agent.
Dynamically bridges the full CBS schema (tbl_customers, tbl_fd_account, etc.)
with the legacy schema (customer, fd, etc.), normalizing records so the AI
agent and validation models work seamlessly on both databases.
"""

from typing import Any, Dict, List, Optional
import os


# Cache schema detection per database
_DETECTED_SCHEMA: Optional[str] = None


def detect_schema_type(cursor) -> str:
    """
    Returns 'cbs' if tbl_customers is present in current database,
    otherwise returns 'legacy'.
    """
    global _DETECTED_SCHEMA
    try:
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.TABLES
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME = 'tbl_customers'
            """
        )
        row = cursor.fetchone()
        count = row[0] if isinstance(row, (tuple, list)) else (row.get("COUNT(*)") if isinstance(row, dict) else 0)
        _DETECTED_SCHEMA = "cbs" if count > 0 else "legacy"
    except Exception:
        _DETECTED_SCHEMA = "legacy"
    return _DETECTED_SCHEMA


def get_schema_type() -> str:
    global _DETECTED_SCHEMA
    if _DETECTED_SCHEMA is not None:
        return _DETECTED_SCHEMA
    return "cbs"


def resolve_table(name: str, schema_type: Optional[str] = None) -> str:
    st = schema_type or get_schema_type()
    if st == "cbs":
        mapping = {
            "customer": "tbl_customers",
            "customers": "tbl_customers",
            "tbl_customers": "tbl_customers",
            "fd": "tbl_fd_account",
            "tbl_fd_account": "tbl_fd_account",
            "fd_masters": "tbl_fd_masters",
            "fd_schemes": "tbl_fd_masters",
            "tbl_fd_masters": "tbl_fd_masters",
            "fd_transactions": "tbl_fd_transaction",
            "tbl_fd_transaction": "tbl_fd_transaction",
            "rd": "tbl_rd_account",
            "tbl_rd_account": "tbl_rd_account",
            "rd_masters": "tbl_rd_masters",
            "rd_schemes": "tbl_rd_masters",
            "tbl_rd_masters": "tbl_rd_masters",
            "rd_transactions": "tbl_rd_transactions",
            "tbl_rd_transactions": "tbl_rd_transactions",
            "share": "tbl_share_account",
            "share_account": "tbl_share_account",
            "tbl_share_account": "tbl_share_account",
            "share_schemes": "tbl_share_account_master",
            "tbl_share_account_master": "tbl_share_account_master",
            "share_transactions": "tbl_share_transactions",
            "tbl_share_transactions": "tbl_share_transactions",
            "sb_account": "tbl_sb_account",
            "tbl_sb_account": "tbl_sb_account",
            "sb_transactions": "tbl_sb_transactions",
            "tbl_sb_transactions": "tbl_sb_transactions",
            "loan_account": "tbl_loan_account",
            "tbl_loan_account": "tbl_loan_account",
        }
        return mapping.get(name.lower(), name)
    else:
        mapping = {
            "tbl_customers": "customer",
            "tbl_fd_account": "fd",
            "tbl_fd_masters": "fd",
            "tbl_fd_transaction": "fd_transactions",
            "tbl_rd_account": "rd",
            "tbl_rd_masters": "rd",
            "tbl_rd_transactions": "fd_transactions",
            "tbl_share_account": "share_account",
            "tbl_share_account_master": "share_account",
            "fd_schemes": "fd",
            "rd_schemes": "rd",
            "share_schemes": "share_account",
        }
        return mapping.get(name.lower(), name)


def normalize_customer_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Standardize a customer row from either CBS or legacy schema
    into a canonical dictionary format.
    """
    if not row:
        return None

    # Handle CBS tbl_customers columns
    if "cust_id" in row or "cust_fname" in row:
        cid = row.get("cust_id")
        fname = row.get("cust_fname") or ""
        lname = row.get("cust_lname") or ""
        phone = row.get("cust_ph_no") or row.get("cust_alt_ph_no") or ""
        aadhaar = row.get("cust_aadhar") or ""
        pan = row.get("cust_pan_no") or ""
        status = (row.get("cust_status") or "ACTIVE").upper()
        reg_date = row.get("cust_reg_date") or row.get("created_at")
        address = row.get("cust_res_address") or row.get("cust_per_address") or ""
        caste = row.get("cust_caste") or ""
        gender = row.get("cust_gender") or ""
        relation_name = row.get("father_name") or row.get("spouse_name") or row.get("relation_name") or ""

        return {
            "customer_id": cid,
            "cust_id": cid,
            "cust_no": row.get("cust_no") or (f"CUST{cid:04d}" if cid else ""),
            "first_name": fname,
            "last_name": lname,
            "name": f"{fname} {lname}".strip(),
            "relation_name": relation_name,
            "phone_no": phone,
            "gender": gender,
            "residential_address": address,
            "caste": caste,
            "aadhaar_no": aadhaar,
            "pan_no": pan,
            "status": status,
            "created_at": reg_date,
            "raw": row,
        }

    # Handle Legacy customer columns
    cid = row.get("customer_id") or row.get("id")
    fname = row.get("first_name") or ""
    lname = row.get("last_name") or ""
    phone = row.get("phone_no") or ""
    aadhaar = row.get("aadhaar_no") or ""
    pan = row.get("pan_no") or ""
    status = (row.get("status") or "ACTIVE").upper()
    created_at = row.get("created_at")
    address = row.get("residential_address") or ""
    caste = row.get("caste") or ""
    relation = row.get("relation_name") or ""
    gender = row.get("gender") or ""

    return {
        "customer_id": cid,
        "cust_id": cid,
        "cust_no": row.get("cust_no") or (f"CUST{cid:04d}" if cid else ""),
        "first_name": fname,
        "last_name": lname,
        "name": f"{fname} {lname}".strip(),
        "relation_name": relation,
        "phone_no": phone,
        "gender": gender,
        "residential_address": address,
        "caste": caste,
        "aadhaar_no": aadhaar,
        "pan_no": pan,
        "status": status,
        "created_at": created_at,
        "raw": row,
    }
