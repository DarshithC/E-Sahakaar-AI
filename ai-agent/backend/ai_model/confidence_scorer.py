# ai_model/confidence_scorer.py

"""
Confidence scoring engine for CBS validation.

Produces an overall confidence score (0-100%) and
risk level (LOW/MEDIUM/HIGH/CRITICAL) based on
individual field validation results.

Zero external AI dependencies.
"""

from typing import Any, Dict, List


# ============================================================
# RISK LEVELS
# ============================================================

RISK_LOW = "LOW"
RISK_MEDIUM = "MEDIUM"
RISK_HIGH = "HIGH"
RISK_CRITICAL = "CRITICAL"


# ============================================================
# FIELD WEIGHTS
# ============================================================

# Each field contributes to the overall score
# based on its importance in CBS banking.

DEFAULT_FIELD_WEIGHTS = {
    "PAN": 15,
    "Aadhaar": 15,
    "Phone": 12,
    "First Name": 8,
    "Last Name": 8,
    "Relation Name": 5,
    "Gender": 5,
    "Address": 10,
    "Status": 12,
    "IFSC": 5,
    "Amount": 5,
}


# ============================================================
# STATUS SCORES
# ============================================================

# How each validation status maps to a score
# multiplier (0.0 to 1.0).

STATUS_SCORES = {
    "VALID": 1.0,
    "VALID_FORMAT": 0.85,
    "VALID_MASKED": 0.70,
    "PARTIAL": 0.50,
    "WARNING": 0.40,
    "SUSPICIOUS": 0.25,
    "MISSING": 0.10,
    "INVALID": 0.0,
    "FAIL": 0.0,
}


# ============================================================
# SCORE CALCULATOR
# ============================================================

def calculate_confidence(
    check_results: List[Dict[str, Any]],
    field_weights: Dict[str, int] = None,
) -> Dict[str, Any]:
    """
    Calculate overall confidence score from
    individual field validation results.

    Each check_result should have:
    - field: str
    - status: str
    - confidence: int (0-100)
    - message: str

    Returns:
    - overall_score: int (0-100)
    - risk_level: str
    - passed: int
    - failed: int
    - warnings: int
    - missing: int
    - checks: list
    - recommendations: list
    """

    weights = field_weights or DEFAULT_FIELD_WEIGHTS

    if not check_results:

        return {
            "overall_score": 0,
            "risk_level": RISK_CRITICAL,
            "passed": 0,
            "failed": 0,
            "warnings": 0,
            "missing": 0,
            "checks": [],
            "recommendations": [
                "No validation data available."
            ],
        }

    total_weight = 0
    weighted_score = 0.0

    passed = 0
    failed = 0
    warnings = 0
    missing = 0

    recommendations = []
    checks = []

    for check in check_results:

        field = check.get("field", "Unknown")
        status = check.get("status", "INVALID")
        confidence = check.get("confidence", 0)
        message = check.get("message", "")

        # Get weight for this field
        weight = weights.get(field, 5)

        total_weight += weight

        # Get score multiplier
        multiplier = STATUS_SCORES.get(
            status, 0.0
        )

        field_score = multiplier * weight

        weighted_score += field_score

        # Classify check outcome
        if status in {"VALID", "VALID_FORMAT"}:
            passed += 1
            icon = "✅"

        elif status == "VALID_MASKED":
            passed += 1
            icon = "🔒"

        elif status in {"WARNING", "SUSPICIOUS"}:
            warnings += 1
            icon = "⚠️"

        elif status == "PARTIAL":
            warnings += 1
            icon = "⚠️"

        elif status == "MISSING":
            missing += 1
            icon = "❌"

        else:
            failed += 1
            icon = "❌"

        checks.append({
            "field": field,
            "value": check.get("value"),
            "status": status,
            "icon": icon,
            "confidence": confidence,
            "message": message,
        })

        # Generate recommendations
        if status == "MISSING":

            recommendations.append(
                f"Provide {field} — this is a mandatory field for CBS compliance."
            )

        elif status in ("INVALID", "FAIL"):

            recommendations.append(
                f"Correct {field} — {message}"
            )

        elif status in ("SUSPICIOUS", "WARNING"):

            recommendations.append(
                f"Verify {field} — {message}"
            )

        elif status == "PARTIAL":

            recommendations.append(
                f"Complete {field} — {message}"
            )

        elif status == "VALID_MASKED":

            recommendations.append(
                f"Consider unmasking {field} for biometric / full e-KYC verification."
            )

    # Calculate overall score
    if total_weight > 0:

        raw_score = (
            weighted_score / total_weight
        ) * 100

        overall_score = max(
            0, min(100, int(round(raw_score)))
        )

    else:

        overall_score = 50

    # Determine risk level
    if failed > 0 or missing > 0:

        risk_level = RISK_CRITICAL

    elif warnings >= 2:

        risk_level = RISK_HIGH

    elif warnings == 1:

        risk_level = RISK_MEDIUM

    else:

        risk_level = RISK_LOW

    return {
        "overall_score": overall_score,
        "risk_level": risk_level,
        "passed": passed,
        "failed": failed,
        "warnings": warnings,
        "missing": missing,
        "total_checks": len(check_results),
        "checks": checks,
        "recommendations": recommendations,
    }


# ============================================================
# SCORE BAR
# ============================================================

def score_bar(score: int) -> str:
    """
    Generate a visual progress bar for the score.

    Example: [■■■■■■■■░░] 80%
    """

    filled = score // 10
    empty = 10 - filled

    return (
        "["
        + "■" * filled
        + "░" * empty
        + f"] {score}%"
    )


# ============================================================
# FRIENDLY FIELD NAMES
# ============================================================

FIELD_NATURAL_NAMES = {
    "PAN": "PAN Card Number",
    "Aadhaar": "Aadhaar Number (UIDAI)",
    "Phone": "Registered Mobile Number",
    "First Name": "First Name",
    "Last Name": "Surname / Last Name",
    "Relation Name": "Father / Guardian Name (C/o)",
    "Gender": "Gender",
    "Address": "Residential Address",
    "Status": "Membership / Account Status",
    "Account Created Date": "Member Registration Date",
    "Duplicate PAN": "Duplicate PAN Card",
    "Duplicate Aadhaar": "Duplicate Aadhaar Number",
    "Duplicate Phone": "Duplicate Mobile Number",
    "IFSC": "Bank IFSC Code",
    "Amount": "Transaction / Deposit Amount",
}


def _get_field_natural_name(field: str) -> str:
    """Return a natural, spoken banking label for a field name."""
    clean = str(field).strip()
    return FIELD_NATURAL_NAMES.get(clean, clean.replace("_", " ").title())


# ============================================================
# FORMAT REPORT
# ============================================================

def format_validation_report(
    customer_info: Dict[str, Any],
    scoring_result: Dict[str, Any],
    anomaly_info: Dict[str, Any] = None,
) -> str:
    """
    Format a human-readable validation report with natural,
    spoken explanations of all invalid fields.
    """

    customer_id = customer_info.get("customer_id", "?")
    name = customer_info.get("name", "Unknown Member")
    score = scoring_result["overall_score"]
    risk = scoring_result["risk_level"]

    risk_badges = {
        "LOW": "🟢 LOW RISK (Compliant)",
        "MEDIUM": "🟡 MEDIUM RISK (Minor warnings)",
        "HIGH": "🟠 HIGH RISK (Needs attention)",
        "CRITICAL": "🔴 CRITICAL (Defects / conflicts detected)",
    }

    lines = [
        f"Validation Report for Member #{customer_id} ({name})",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"Overall Confidence: {score_bar(score)}",
        f"Compliance Risk Level: {risk_badges.get(risk, risk)}",
        "",
        "📋 Field Verification Summary:",
    ]

    # Individual check summary list
    invalid_checks = []
    warning_checks = []

    for check in scoring_result["checks"]:
        field_label = _get_field_natural_name(check["field"])
        status = check["status"]

        lines.append(
            f"  {check['icon']} {field_label}: {check['message']}"
        )

        if status in ("INVALID", "FAIL", "MISSING"):
            invalid_checks.append(check)
        elif status in ("WARNING", "SUSPICIOUS", "PARTIAL"):
            warning_checks.append(check)

    # Anomaly detection results
    if anomaly_info:
        anomaly_score = anomaly_info.get("anomaly_score", 0)
        is_anomaly = anomaly_info.get("is_anomaly", False)
        lines.append("")

        if is_anomaly:
            lines.append(
                f"🔍 Pattern & Anomaly Analysis: ⚠️ FLAGGED (Score: {anomaly_score:.2f})"
            )
            for reason in anomaly_info.get("reasons", []):
                lines.append(f"   • {reason}")
        else:
            lines.append(
                f"🔍 Pattern & Anomaly Analysis: NORMAL (Score: {anomaly_score:.2f})"
            )

    # ========================================================
    # HUMAN-READABLE INVALID FIELDS EXPLANATION
    # ========================================================
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    if invalid_checks or warning_checks:
        lines.append("🚨 Field Issues & Required Rectification:")
        lines.append(
            f"We detected {len(invalid_checks)} defective field(s) "
            f"and {len(warning_checks)} warning(s) that require review:\n"
        )

        counter = 1

        # Explain each invalid field in plain conversational English
        for chk in invalid_checks:
            field_name = _get_field_natural_name(chk["field"])
            val = chk.get("value")
            val_display = f'"{val}"' if val is not None and str(val).strip() else "None (Empty / Not provided)"
            msg = chk.get("message", "Validation failed.")

            lines.append(f"{counter}. {field_name}:")
            lines.append(f"   • Current Status: DEFECTIVE / INVALID")
            lines.append(f"   • Value on Record: {val_display}")
            lines.append(f"   • What is Wrong: {msg}")

            # Specific practical guidance
            field_clean = chk["field"].upper()
            if "DUPLICATE" in field_clean:
                lines.append("   • Action Needed: Verify whether this is a shared household contact or update the record with the member's unique personal identity/mobile number.")
            elif "PAN" in field_clean:
                lines.append("   • Action Needed: Obtain a verified copy of the member's PAN card. Update the record with the exact 10-character alphanumeric PAN (5 letters, 4 digits, 1 letter).")
            elif "AADHAAR" in field_clean:
                lines.append("   • Action Needed: Obtain the 12-digit Aadhaar number from the member. Ensure it contains 12 digits and does not start with 0 or 1, or store in approved masked format (XXXX XXXX 1234).")
            elif "PHONE" in field_clean:
                lines.append("   • Action Needed: Provide a valid 10-digit Indian mobile number starting with 6, 7, 8, or 9 for SMS alerts.")
            elif "NAME" in field_clean:
                lines.append("   • Action Needed: Enter a valid member name containing alphabets only (at least 2 characters).")
            elif "ADDRESS" in field_clean:
                lines.append("   • Action Needed: Provide the complete residential street address along with the 6-digit postal PIN code.")
            else:
                lines.append(f"   • Action Needed: Please rectify this field in the CBS member portal to achieve full compliance.")

            lines.append("")
            counter += 1

        # Warnings / Advisory notes
        for chk in warning_checks:
            field_name = _get_field_natural_name(chk["field"])
            msg = chk.get("message", "Review recommended.")
            lines.append(f"{counter}. {field_name} (Advisory / Warning):")
            lines.append(f"   • Note: {msg}")
            lines.append(f"   • Suggestion: Update or verify this field to improve record quality.")
            lines.append("")
            counter += 1

    else:
        # All valid - positive reinforcement
        lines.append("✅ Validation Outcome: ALL FIELDS FULLY VALID & COMPLIANT")
        lines.append(
            f"All submitted fields for Member #{customer_id} ({name}) — including PAN card, "
            f"Aadhaar number, registered mobile number, residential address, name, and account status — "
            f"meet CBS platform standards. No defects, duplicates, or anomalies were detected."
        )

    # General Recommendations
    recommendations = scoring_result.get("recommendations", [])
    if recommendations and not invalid_checks:
        lines.append("")
        lines.append("💡 Best Practice Suggestions:")
        for rec in recommendations:
            lines.append(f"• {rec}")

    return "\n".join(lines)
