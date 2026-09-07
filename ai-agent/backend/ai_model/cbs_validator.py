# ai_model/cbs_validator.py

"""
CBS Validation Engine — Main Orchestrator.

This is the core of the custom AI model.
It runs 15+ validation checks across customers,
accounts, and transactions, then produces a
confidence-scored validation report.

Zero external AI dependencies.
"""

import re
from typing import Any, Dict, List, Optional

from ai_model.field_validators import (
    validate_pan,
    validate_aadhaar,
    validate_phone,
    validate_name,
    validate_address,
    validate_gender,
    validate_status,
    validate_required,
    validate_amount,
    validate_date_sanity,
    validate_ifsc,
)

from ai_model.confidence_scorer import (
    calculate_confidence,
    format_validation_report,
    _get_field_natural_name,
)

from ai_model.anomaly_detector import (
    get_detector,
)

from schema_adapter import resolve_table, normalize_customer_row


# ============================================================
# DATABASE HELPERS
# ============================================================

_db_fetch_all = None
_db_fetch_one = None


def set_database_functions(fetch_all, fetch_one):
    """
    Set the database query functions.
    Called once during server startup.
    """

    global _db_fetch_all, _db_fetch_one

    _db_fetch_all = fetch_all
    _db_fetch_one = fetch_one


def _fetch_all(sql, params=()):
    """Safe wrapper for database fetch_all."""

    if _db_fetch_all is None:
        return []

    try:
        return _db_fetch_all(sql, params)
    except Exception as exc:
        print(f"[CBS VALIDATOR DB ERROR] {repr(exc)}")
        return []


def _fetch_one(sql, params=()):
    """Safe wrapper for database fetch_one."""

    if _db_fetch_one is None:
        return None

    try:
        return _db_fetch_one(sql, params)
    except Exception as exc:
        print(f"[CBS VALIDATOR DB ERROR] {repr(exc)}")
        return None


# ============================================================
# DUPLICATE DETECTION
# ============================================================

def check_duplicates(
    customer_id: int,
    customer: Dict[str, Any],
) -> Dict[str, Dict[str, Any]]:
    """
    Check for duplicate PAN, Aadhaar, and Phone
    across all customers.
    """

    duplicates = {}
    tbl = resolve_table("customer")
    is_cbs = (tbl == "tbl_customers")

    id_col = "cust_id" if is_cbs else "customer_id"
    fname_col = "cust_fname" if is_cbs else "first_name"
    lname_col = "cust_lname" if is_cbs else "last_name"
    aadhaar_col = "cust_aadhar" if is_cbs else "aadhaar_no"
    pan_col = "cust_pan_no" if is_cbs else "pan_no"
    phone_col = "cust_ph_no" if is_cbs else "phone_no"

    # Duplicate Aadhaar
    aadhaar = str(
        customer.get("aadhaar_no") or ""
    ).strip()

    if aadhaar and "X" not in aadhaar.upper():

        rows = _fetch_all(
            f"""
            SELECT {id_col} AS customer_id, {fname_col} AS first_name, {lname_col} AS last_name
            FROM {tbl}
            WHERE {aadhaar_col} = %s
              AND {id_col} <> %s
            LIMIT 3
            """,
            (aadhaar, customer_id)
        )

        duplicates["Aadhaar"] = {
            "count": len(rows),
            "field": "aadhaar_no",
            "value": aadhaar,
            "conflicts": [
                f"Member #{r['customer_id']} ({r.get('first_name', '')} {r.get('last_name', '')}".strip() + ")"
                for r in rows
            ],
        }

    # Duplicate PAN
    pan = str(
        customer.get("pan_no") or ""
    ).strip()

    if pan and len(pan) == 10:

        rows = _fetch_all(
            f"""
            SELECT {id_col} AS customer_id, {fname_col} AS first_name, {lname_col} AS last_name
            FROM {tbl}
            WHERE {pan_col} = %s
              AND {id_col} <> %s
            LIMIT 3
            """,
            (pan, customer_id)
        )

        duplicates["PAN"] = {
            "count": len(rows),
            "field": "pan_no",
            "value": pan,
            "conflicts": [
                f"Member #{r['customer_id']} ({r.get('first_name', '')} {r.get('last_name', '')}".strip() + ")"
                for r in rows
            ],
        }

    # Duplicate Phone
    phone = str(
        customer.get("phone_no") or ""
    ).strip()

    if phone and len(phone) >= 10:

        rows = _fetch_all(
            f"""
            SELECT {id_col} AS customer_id, {fname_col} AS first_name, {lname_col} AS last_name
            FROM {tbl}
            WHERE {phone_col} = %s
              AND {id_col} <> %s
            LIMIT 3
            """,
            (phone, customer_id)
        )

        duplicates["Phone"] = {
            "count": len(rows),
            "field": "phone_no",
            "value": phone,
            "conflicts": [
                f"Member #{r['customer_id']} ({r.get('first_name', '')} {r.get('last_name', '')}".strip() + ")"
                for r in rows
            ],
        }

    return duplicates


# ============================================================
# CUSTOMER VALIDATION
# ============================================================

def validate_customer_full(
    customer_id: int,
) -> Dict[str, Any]:
    """
    Run full CBS validation on a customer.

    This is the main entry point for customer validation.
    Runs all field validators, duplicate checks,
    anomaly detection, and confidence scoring.

    Returns a complete validation report.
    """

    # ========================================================
    # 1. FETCH CUSTOMER
    # ========================================================

    tbl = resolve_table("customer")
    id_col = "cust_id" if tbl == "tbl_customers" else "customer_id"

    raw_customer = _fetch_one(
        f"""
        SELECT *
        FROM {tbl}
        WHERE {id_col} = %s
        """,
        (customer_id,)
    )

    customer = normalize_customer_row(raw_customer)

    if not customer:

        return {
            "success": False,
            "error": (
                f"Customer {customer_id} "
                "was not found in the database."
            ),
            "report": (
                f"Customer {customer_id} "
                "was not found in the database."
            ),
        }

    # ========================================================
    # 2. RUN FIELD VALIDATIONS
    # ========================================================

    checks = []

    # PAN
    checks.append(
        validate_pan(
            customer.get("pan_no")
        )
    )

    # Aadhaar
    checks.append(
        validate_aadhaar(
            customer.get("aadhaar_no")
        )
    )

    # Phone
    checks.append(
        validate_phone(
            customer.get("phone_no")
        )
    )

    # First Name
    checks.append(
        validate_name(
            customer.get("first_name"),
            "First Name"
        )
    )

    # Last Name
    checks.append(
        validate_name(
            customer.get("last_name"),
            "Last Name"
        )
    )

    # Relation Name
    checks.append(
        validate_name(
            customer.get("relation_name"),
            "Relation Name"
        )
    )

    # Gender
    checks.append(
        validate_gender(
            customer.get("gender")
        )
    )

    # Address
    checks.append(
        validate_address(
            customer.get("residential_address")
        )
    )

    # Status
    checks.append(
        validate_status(
            customer.get("status")
        )
    )

    # Created date sanity
    if customer.get("created_at"):

        checks.append(
            validate_date_sanity(
                customer.get("created_at"),
                "Account Created Date"
            )
        )

    # ========================================================
    # 3. DUPLICATE DETECTION
    # ========================================================

    duplicates = check_duplicates(
        customer_id, customer
    )

    # Add duplicate results to checks
    for field, dup_info in duplicates.items():

        field_name = "Mobile Number" if field == "Phone" else ("PAN Card" if field == "PAN" else "Aadhaar Number")
        val = dup_info.get("value")

        if dup_info["count"] > 0:

            conflicts_str = ", ".join(dup_info.get("conflicts", [])) or f"{dup_info['count']} other account(s)"

            checks.append({
                "field": f"Duplicate {field}",
                "value": val,
                "status": "FAIL",
                "confidence": 95,
                "message": (
                    f"This {field_name.lower()} is already registered under {conflicts_str}."
                ),
            })

        else:

            checks.append({
                "field": f"Duplicate {field}",
                "value": val,
                "status": "VALID",
                "confidence": 95,
                "message": (
                    f"No duplicate {field_name.lower()} found across CBS records."
                ),
            })

    # ========================================================
    # 4. ANOMALY DETECTION
    # ========================================================

    detector = get_detector()

    anomaly_info = detector.score_customer(
        customer
    )

    # ========================================================
    # 5. CONFIDENCE SCORING
    # ========================================================

    scoring = calculate_confidence(checks)

    # ========================================================
    # 6. BUILD CUSTOMER INFO
    # ========================================================

    name = (
        f"{customer.get('first_name', '')} "
        f"{customer.get('last_name', '')}"
    ).strip()

    customer_info = {
        "customer_id": customer_id,
        "name": name or "Unknown",
        "duplicates": duplicates,
    }

    # ========================================================
    # 7. FORMAT REPORT
    # ========================================================

    report = format_validation_report(
        customer_info,
        scoring,
        anomaly_info,
    )

    return {
        "success": True,
        "customer_id": customer_id,
        "name": name,
        "overall_score": scoring["overall_score"],
        "risk_level": scoring["risk_level"],
        "passed": scoring["passed"],
        "failed": scoring["failed"],
        "warnings": scoring["warnings"],
        "missing": scoring["missing"],
        "total_checks": scoring["total_checks"],
        "checks": scoring["checks"],
        "anomaly": anomaly_info,
        "duplicates": duplicates,
        "recommendations": scoring["recommendations"],
        "report": report,
    }


# ============================================================
# BULK CUSTOMER VALIDATION (HUMAN SPOKEN LANGUAGE, NO SCORES)
# ============================================================

def _format_spoken_field_defect(chk: Dict[str, Any]) -> str:
    """
    Format a defective field check into clean, legible banking language.
    Explicitly does NOT output any numerical score or percentage.
    """
    field = chk.get("field", "")
    natural_name = _get_field_natural_name(field)
    msg = chk.get("message", "Validation issue detected.")
    status = chk.get("status", "")
    val = chk.get("value")
    field_upper = field.upper()

    if "DUPLICATE" in field_upper:
        return f"• Contact Conflict: {msg}"

    if status == "MISSING" or val is None or str(val).strip() == "":
        if "PAN" in field_upper:
            return "• PAN Card: Missing (Mandatory 10-character PAN card is not recorded)"
        elif "AADHAAR" in field_upper:
            return "• Aadhaar Card: Missing (Mandatory 12-digit UIDAI number is not recorded)"
        elif "PHONE" in field_upper or "MOBILE" in field_upper:
            return "• Mobile Number: Missing (No 10-digit Indian mobile recorded)"
        elif "ADDRESS" in field_upper:
            return "• Address: Missing (Residential address not recorded)"
        else:
            return f"• {natural_name}: Missing from member record"

    if "PAN" in field_upper:
        return f"• PAN Card: Invalid value '{val}' ({msg})"
    elif "AADHAAR" in field_upper:
        return f"• Aadhaar Card: Invalid value '{val}' ({msg})"
    elif "PHONE" in field_upper or "MOBILE" in field_upper:
        return f"• Mobile Number: Invalid value '{val}' ({msg})"
    else:
        return f"• {natural_name}: Invalid value '{val}' ({msg})"


def _format_spoken_field_advisory(chk: Dict[str, Any]) -> str:
    """Format an advisory note in clean legible language."""
    field = chk.get("field", "")
    natural_name = _get_field_natural_name(field)
    msg = chk.get("message", "Review recommended.")
    return f"• Advisory: {natural_name} — {msg}"


def validate_all_customers() -> Dict[str, Any]:
    """
    Validate all customers in the database.
    Returns a summary report.
    """

    tbl = resolve_table("customer")
    id_col = "cust_id" if tbl == "tbl_customers" else "customer_id"

    raw_rows = _fetch_all(
        f"""
        SELECT *
        FROM {tbl}
        ORDER BY {id_col}
        """,
        ()
    )

    rows = [normalize_customer_row(r) for r in (raw_rows or []) if r]

    if not rows:

        return {
            "success": True,
            "total": 0,
            "report": (
                "No customers found in the database."
            ),
        }

    results = []
    critical = []
    high_risk = []
    valid = []

    for row in rows:

        cid = row["customer_id"]

        result = validate_customer_full(cid)

        if not result.get("success"):
            continue

        name = (
            f"{row.get('first_name', '')} "
            f"{row.get('last_name', '')}"
        ).strip()

        defects = [
            chk for chk in result.get("checks", [])
            if chk.get("status") in ("INVALID", "FAIL", "MISSING")
        ]
        warnings_list = [
            chk for chk in result.get("checks", [])
            if chk.get("status") in ("WARNING", "SUSPICIOUS", "PARTIAL")
        ]

        entry = {
            "customer_id": cid,
            "name": name,
            "score": result["overall_score"],
            "risk": result["risk_level"],
            "failed": result["failed"],
            "warnings": result["warnings"],
            "defects": defects,
            "warnings_list": warnings_list,
        }

        results.append(entry)

        if result["risk_level"] == "CRITICAL":
            critical.append(entry)

        elif result["risk_level"] == "HIGH":
            high_risk.append(entry)

        else:
            valid.append(entry)

    # Build human-readable summary report in everyday spoken banking language (NO SCORES)
    total_members = len(results)
    attention_members = critical + high_risk

    lines = []

    if not attention_members:
        lines.append(
            f"All {total_members} registered members have clean, fully verified KYC and identity records in our CBS system. No invalid or defective accounts were found."
        )
        return {
            "success": True,
            "total": len(results),
            "critical_count": len(critical),
            "high_risk_count": len(high_risk),
            "valid_count": len(valid),
            "results": results,
            "report": "\n".join(lines),
        }

    lines.append(
        f"There are currently {len(attention_members)} member account(s) with invalid or missing KYC data (out of {total_members} total registered members):"
    )
    lines.append("")

    for idx, item in enumerate(attention_members, start=1):
        cid = item["customer_id"]
        name = item["name"]
        defects = item.get("defects", [])
        warnings_list = item.get("warnings_list", [])

        lines.append(f"{idx}. Member #{cid} — {name}:")

        if defects:
            for d in defects:
                lines.append(f"   {_format_spoken_field_defect(d)}")

        if warnings_list:
            for w in warnings_list:
                lines.append(f"   {_format_spoken_field_advisory(w)}")

        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append(
        f"Summary: Out of {total_members} total members audited, {len(valid)} members are fully verified and compliant. The {len(attention_members)} member(s) listed above require KYC updates."
    )

    return {
        "success": True,
        "total": len(results),
        "critical_count": len(critical),
        "high_risk_count": len(high_risk),
        "valid_count": len(valid),
        "results": results,
        "report": "\n".join(lines),
    }


# ============================================================
# VALIDATE SPECIFIC SCOPE (LAST ONBOARDED)
# ============================================================

def validate_customer_list(
    customer_ids: List[int],
) -> str:
    """
    Validate a list of customers and return
    a combined report string.
    """

    if not customer_ids:

        return "No customer IDs provided for validation."

    reports = []

    for cid in customer_ids:

        result = validate_customer_full(cid)

        reports.append(
            result.get(
                "report",
                f"Validation failed for customer {cid}."
            )
        )

    return "\n\n".join(reports)


# ============================================================
# QUICK PAN/AADHAAR VALIDATION (BACKWARD COMPAT)
# ============================================================

def quick_validate_customer(
    customer_id: int,
    scope: str = "all",
) -> str:
    """
    Quick validation for backward compatibility
    with existing validation intent handlers.

    scope: "pan", "aadhaar", or "all"
    """

    tbl = resolve_table("customer")
    id_col = "cust_id" if tbl == "tbl_customers" else "customer_id"

    raw = _fetch_one(
        f"""
        SELECT *
        FROM {tbl}
        WHERE {id_col} = %s
        """,
        (customer_id,)
    )
    customer = normalize_customer_row(raw)

    if not customer:

        return (
            f"Customer {customer_id} "
            "was not found in the database."
        )

    name = (
        f"{customer.get('first_name', '')} "
        f"{customer.get('last_name', '')}"
    ).strip()

    results = []

    if scope in ("pan", "all"):

        pan_result = validate_pan(
            customer.get("pan_no")
        )

        results.append(
            f"PAN: {pan_result['message']}"
        )

        if pan_result.get("entity_type"):

            results.append(
                f"  Entity Type: "
                f"{pan_result['entity_type']}"
            )

    if scope in ("aadhaar", "all"):

        aadhaar_result = validate_aadhaar(
            customer.get("aadhaar_no")
        )

        results.append(
            f"Aadhaar: {aadhaar_result['message']}"
        )

    header = (
        f"Validation for customer "
        f"{customer_id} ({name}):\n"
    )

    return header + "\n".join(results)
