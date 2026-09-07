# ai_model/field_validators.py

"""
Enhanced field-level validators for CBS banking data.

Goes beyond simple regex — includes checksum verification,
carrier detection, CBS-specific format validation, and
intelligent error messages.

Zero external AI dependencies. Pure Python.
"""

import re
from typing import Any, Dict, Optional, Tuple


# ============================================================
# PAN VALIDATION
# ============================================================

# 4th character of PAN indicates entity type
PAN_ENTITY_TYPES = {
    "A": "Association of Persons (AOP)",
    "B": "Body of Individuals (BOI)",
    "C": "Company",
    "F": "Firm",
    "G": "Government",
    "H": "Hindu Undivided Family (HUF)",
    "L": "Local Authority",
    "J": "Artificial Juridical Person",
    "P": "Individual / Person",
    "T": "Trust (AOP)",
}


def validate_pan(pan: Any) -> Dict[str, Any]:
    """
    Validate PAN with format check + entity type detection.

    PAN Format: AAAAA9999A
    - Positions 1-5: Uppercase letters
    - Positions 6-9: Digits
    - Position 10: Uppercase letter (check letter)
    - Position 4: Entity type indicator
    """

    result = {
        "field": "PAN",
        "value": None,
        "status": "INVALID",
        "message": "",
        "entity_type": None,
        "confidence": 0,
    }

    if pan is None or str(pan).strip() == "":

        result["status"] = "MISSING"
        result["message"] = "PAN number is not provided."
        result["confidence"] = 0

        return result

    value = str(pan).strip().upper()

    result["value"] = value

    if len(value) != 10:

        result["message"] = (
            f"PAN must be exactly 10 characters, "
            f"but got {len(value)}."
        )
        result["confidence"] = 10

        return result

    pattern = r"[A-Z]{5}[0-9]{4}[A-Z]"

    if not re.fullmatch(pattern, value):

        # Provide specific feedback on what's wrong
        issues = []

        if not re.match(r"[A-Z]{5}", value[:5]):
            issues.append(
                "first 5 characters must be letters"
            )

        if not re.match(r"[0-9]{4}", value[5:9]):
            issues.append(
                "characters 6-9 must be digits"
            )

        if not re.match(r"[A-Z]", value[9]):
            issues.append(
                "last character must be a letter"
            )

        result["message"] = (
            "Invalid PAN format: "
            + "; ".join(issues)
            + "."
        )
        result["confidence"] = 20

        return result

    # Valid format — check entity type
    entity_char = value[3]
    entity_type = PAN_ENTITY_TYPES.get(
        entity_char
    )

    if entity_type:

        result["entity_type"] = entity_type
        result["status"] = "VALID"
        result["confidence"] = 95
        result["message"] = (
            f"Valid PAN format — "
            f"{entity_type}."
        )

    else:

        result["status"] = "VALID"
        result["confidence"] = 80
        result["message"] = (
            f"Valid PAN format, but entity "
            f"type '{entity_char}' is unusual."
        )

    return result


# ============================================================
# AADHAAR VALIDATION (WITH VERHOEFF CHECKSUM)
# ============================================================

# Verhoeff tables for checksum calculation
_VERHOEFF_D = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_VERHOEFF_P = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def _verhoeff_checksum(number_str: str) -> bool:
    """
    Verify Verhoeff checksum.
    UIDAI uses Verhoeff algorithm for Aadhaar validation.
    """

    c = 0

    for i, digit in enumerate(
        reversed(number_str)
    ):

        c = _VERHOEFF_D[c][
            _VERHOEFF_P[i % 8][int(digit)]
        ]

    return c == 0


def validate_aadhaar(aadhaar: Any) -> Dict[str, Any]:
    """
    Validate Aadhaar number.

    Checks:
    - 12-digit numeric format
    - Does not start with 0 or 1
    - Verhoeff checksum on unmasked numbers
    - Masked format detection (XXXX XXXX 1234)
    """

    result = {
        "field": "Aadhaar",
        "value": None,
        "status": "INVALID",
        "message": "",
        "is_masked": False,
        "confidence": 0,
    }

    if aadhaar is None or str(aadhaar).strip() == "":

        result["status"] = "MISSING"
        result["message"] = (
            "Aadhaar number is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(aadhaar).strip()

    result["value"] = value

    # Detect masked Aadhaar
    if "X" in value.upper() or "x" in value:

        result["is_masked"] = True

        # Check masked format
        masked_pattern = (
            r"[Xx]{4}\s*[Xx]{4}\s*\d{4}"
        )

        if re.fullmatch(masked_pattern, value):

            result["status"] = "VALID_MASKED"
            result["confidence"] = 70
            result["message"] = (
                "Aadhaar is stored in masked format. "
                "Last 4 digits are visible. Full "
                "verification requires unmasked number."
            )

        else:

            result["status"] = "PARTIAL"
            result["confidence"] = 40
            result["message"] = (
                "Aadhaar appears to be partially "
                "masked but the format is not standard."
            )

        return result

    # Extract digits
    digits = re.sub(r"\D", "", value)

    if len(digits) != 12:

        result["message"] = (
            f"Aadhaar must be exactly 12 digits, "
            f"but got {len(digits)}."
        )
        result["confidence"] = 10

        return result

    # Aadhaar cannot start with 0 or 1
    if digits[0] in ("0", "1"):

        result["message"] = (
            "Aadhaar number cannot start "
            "with 0 or 1."
        )
        result["confidence"] = 15

        return result

    # Verhoeff checksum
    if _verhoeff_checksum(digits):

        result["status"] = "VALID"
        result["confidence"] = 98
        result["message"] = (
            "Valid Aadhaar format with "
            "correct checksum."
        )

    else:

        result["status"] = "VALID_FORMAT"
        result["confidence"] = 75
        result["message"] = (
            "Valid 12-digit Aadhaar format, but "
            "Verhoeff checksum did not pass. "
            "The number may have a typo."
        )

    return result


# ============================================================
# PHONE VALIDATION
# ============================================================

# Indian mobile carrier prefix ranges
CARRIER_PREFIXES = {
    "Jio": [
        "60", "61", "62", "63", "64",
        "65", "66", "67", "68", "69",
        "70", "71", "72", "73", "74",
        "75", "76", "77", "78", "79",
        "80", "81", "82", "83", "84",
        "85", "86", "87", "88", "89",
    ],
    "Airtel": [
        "70", "72", "73", "74",
        "75", "79", "80", "81",
        "84", "89", "96", "97", "98",
    ],
    "Vi (Vodafone-Idea)": [
        "70", "72", "75", "76",
        "77", "78", "79", "81",
        "82", "86", "97", "98",
    ],
    "BSNL": [
        "94", "74", "78",
    ],
}


def _detect_carrier(phone: str) -> Optional[str]:
    """Best-effort carrier detection from prefix."""

    if len(phone) < 2:
        return None

    prefix = phone[:2]

    # Check most specific first (BSNL)
    for carrier, prefixes in CARRIER_PREFIXES.items():

        if prefix in prefixes:
            return carrier

    return "Unknown carrier"


def validate_phone(phone: Any) -> Dict[str, Any]:
    """
    Validate Indian 10-digit mobile number.

    Checks:
    - Must be exactly 10 digits
    - Must start with 6, 7, 8, or 9
    - Carrier prefix detection
    """

    result = {
        "field": "Phone",
        "value": None,
        "status": "INVALID",
        "message": "",
        "carrier": None,
        "confidence": 0,
    }

    if phone is None or str(phone).strip() == "":

        result["status"] = "MISSING"
        result["message"] = (
            "Phone number is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(phone).strip()

    result["value"] = value

    # Remove common prefixes
    clean = value

    if clean.startswith("+91"):
        clean = clean[3:]

    elif clean.startswith("91") and len(clean) == 12:
        clean = clean[2:]

    elif clean.startswith("0"):
        clean = clean[1:]

    clean = re.sub(r"[\s\-()]", "", clean)

    if not clean.isdigit():

        result["message"] = (
            "Phone number contains "
            "non-numeric characters."
        )
        result["confidence"] = 10

        return result

    if len(clean) != 10:

        result["message"] = (
            f"Phone must be 10 digits, "
            f"but got {len(clean)}."
        )
        result["confidence"] = 15

        return result

    if clean[0] not in "6789":

        result["message"] = (
            "Indian mobile numbers must "
            "start with 6, 7, 8, or 9."
        )
        result["confidence"] = 20

        return result

    # All same digits is suspicious
    if len(set(clean)) == 1:

        result["status"] = "SUSPICIOUS"
        result["confidence"] = 30
        result["message"] = (
            "Phone number has all identical "
            "digits — likely invalid."
        )

        return result

    carrier = _detect_carrier(clean)

    result["status"] = "VALID"
    result["confidence"] = 90
    result["carrier"] = carrier
    result["message"] = (
        f"Valid Indian mobile number"
        + (
            f" (likely {carrier})"
            if carrier
            else ""
        )
        + "."
    )

    return result


# ============================================================
# NAME VALIDATION
# ============================================================

def validate_name(
    name: Any,
    field_label: str = "Name"
) -> Dict[str, Any]:
    """
    Validate a person's name field.

    Checks:
    - Not empty
    - Minimum length (2 characters)
    - No digits
    - No excessive special characters
    """

    result = {
        "field": field_label,
        "value": None,
        "status": "INVALID",
        "message": "",
        "confidence": 0,
    }

    if name is None or str(name).strip() == "":

        result["status"] = "MISSING"
        result["message"] = (
            f"{field_label} is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(name).strip()

    result["value"] = value

    if len(value) < 2:

        result["message"] = (
            f"{field_label} is too short "
            f"(minimum 2 characters)."
        )
        result["confidence"] = 15

        return result

    if len(value) > 100:

        result["message"] = (
            f"{field_label} is too long "
            f"(maximum 100 characters)."
        )
        result["confidence"] = 20

        return result

    # Names should not contain digits
    if re.search(r"\d", value):

        result["message"] = (
            f"{field_label} should not "
            "contain numbers."
        )
        result["confidence"] = 25

        return result

    # Check for excessive special characters
    special_count = len(
        re.findall(r"[^a-zA-Z\s.\-']", value)
    )

    if special_count > 2:

        result["status"] = "SUSPICIOUS"
        result["confidence"] = 50
        result["message"] = (
            f"{field_label} contains unusual "
            "special characters."
        )

        return result

    result["status"] = "VALID"
    result["confidence"] = 90
    result["message"] = (
        f"{field_label} format looks valid."
    )

    return result


# ============================================================
# ADDRESS VALIDATION
# ============================================================

# Indian PIN code regex
PIN_CODE_PATTERN = re.compile(
    r"\b[1-9][0-9]{5}\b"
)


def validate_address(
    address: Any
) -> Dict[str, Any]:
    """
    Validate residential address.

    Checks:
    - Not empty
    - Minimum length
    - PIN code extraction
    """

    result = {
        "field": "Address",
        "value": None,
        "status": "INVALID",
        "message": "",
        "pin_code": None,
        "has_pin_code": False,
        "confidence": 0,
    }

    if (
        address is None
        or str(address).strip() == ""
    ):

        result["status"] = "MISSING"
        result["message"] = (
            "Residential address is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(address).strip()

    result["value"] = value

    if len(value) < 10:

        result["message"] = (
            "Address is too short to be "
            "a complete address."
        )
        result["confidence"] = 20

        return result

    # Check for PIN code
    pin_match = PIN_CODE_PATTERN.search(value)

    if pin_match:

        result["pin_code"] = pin_match.group()
        result["has_pin_code"] = True

    # Score the address
    address_lower = value.lower()

    components = 0

    # Check for common address components
    address_keywords = [
        "house", "no", "street", "road",
        "lane", "nagar", "colony",
        "village", "town", "city",
        "district", "state", "post",
        "taluk", "mandal",
        "flat", "apartment", "building",
        "floor", "sector", "block",
        "ward", "municipal", "panchayat",
    ]

    for keyword in address_keywords:

        if keyword in address_lower:
            components += 1

    if result["has_pin_code"]:
        components += 2

    if components >= 3:

        result["status"] = "VALID"
        result["confidence"] = 90
        result["message"] = "Address looks complete."

    elif components >= 1:

        result["status"] = "PARTIAL"
        result["confidence"] = 60
        result["message"] = (
            "Address is present but may be "
            "incomplete."
            + (
                ""
                if result["has_pin_code"]
                else " Missing PIN code."
            )
        )

    else:

        result["status"] = "VALID"
        result["confidence"] = 70
        result["message"] = (
            "Address is provided."
            + (
                ""
                if result["has_pin_code"]
                else " Consider adding PIN code."
            )
        )

    return result


# ============================================================
# GENDER VALIDATION
# ============================================================

VALID_GENDERS = {
    "m": "Male",
    "f": "Female",
    "male": "Male",
    "female": "Female",
    "o": "Other",
    "other": "Other",
    "t": "Transgender",
    "transgender": "Transgender",
}


def validate_gender(
    gender: Any
) -> Dict[str, Any]:
    """Validate gender field."""

    result = {
        "field": "Gender",
        "value": None,
        "status": "INVALID",
        "message": "",
        "confidence": 0,
    }

    if gender is None or str(gender).strip() == "":

        result["status"] = "MISSING"
        result["message"] = (
            "Gender is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(gender).strip()

    result["value"] = value

    normalized = value.lower().strip()

    if normalized in VALID_GENDERS:

        result["status"] = "VALID"
        result["confidence"] = 95
        result["message"] = (
            f"Gender: "
            f"{VALID_GENDERS[normalized]}."
        )

    else:

        result["message"] = (
            f"Gender '{value}' is not recognized. "
            "Expected: Male, Female, or Other."
        )
        result["confidence"] = 20

    return result


# ============================================================
# STATUS VALIDATION
# ============================================================

VALID_STATUSES = {
    "active", "approved",
    "pending", "pending approval",
    "approval pending",
    "inactive", "blocked",
    "rejected", "closed",
    "suspended", "dormant",
}


def validate_status(
    status: Any
) -> Dict[str, Any]:
    """Validate customer status field."""

    result = {
        "field": "Status",
        "value": None,
        "status": "INVALID",
        "message": "",
        "risk_flag": False,
        "confidence": 0,
    }

    if status is None or str(status).strip() == "":

        result["status"] = "MISSING"
        result["message"] = (
            "Customer status is not provided."
        )
        result["confidence"] = 0

        return result

    value = str(status).strip()

    result["value"] = value

    normalized = value.lower().strip()

    if normalized in {"active", "approved"}:

        result["status"] = "VALID"
        result["confidence"] = 95
        result["message"] = (
            f"Customer status is {value} — "
            "fully operational."
        )

    elif normalized in {
        "pending",
        "pending approval",
        "approval pending",
    }:

        result["status"] = "WARNING"
        result["confidence"] = 80
        result["risk_flag"] = True
        result["message"] = (
            "Customer approval is still pending."
        )

    elif normalized in {
        "rejected",
        "inactive",
        "blocked",
        "suspended",
        "closed",
        "dormant",
    }:

        result["status"] = "FAIL"
        result["confidence"] = 95
        result["risk_flag"] = True
        result["message"] = (
            f"Customer status is {value.upper()} "
            "— account operations may be restricted."
        )

    elif normalized in VALID_STATUSES:

        result["status"] = "VALID"
        result["confidence"] = 85
        result["message"] = (
            f"Customer status: {value}."
        )

    else:

        result["status"] = "WARNING"
        result["confidence"] = 50
        result["risk_flag"] = True
        result["message"] = (
            f"Unrecognized status: '{value}'. "
            "This may need review."
        )

    return result


# ============================================================
# REQUIRED FIELD CHECK
# ============================================================

def validate_required(
    value: Any,
    field_label: str
) -> Dict[str, Any]:
    """Check if a required field has data."""

    result = {
        "field": field_label,
        "value": None,
        "status": "MISSING",
        "message": "",
        "confidence": 0,
    }

    if value is None:

        result["message"] = (
            f"{field_label} is not provided."
        )

        return result

    clean = str(value).strip()

    if not clean:

        result["message"] = (
            f"{field_label} is empty."
        )

        return result

    result["value"] = clean
    result["status"] = "VALID"
    result["confidence"] = 90
    result["message"] = (
        f"{field_label} is provided."
    )

    return result


# ============================================================
# IFSC CODE VALIDATION
# ============================================================

def validate_ifsc(ifsc: Any) -> Dict[str, Any]:
    """
    Validate IFSC code format.

    Format: 4 letter bank code + 0 + 6 char branch code
    Example: SBIN0001234
    """

    result = {
        "field": "IFSC",
        "value": None,
        "status": "INVALID",
        "message": "",
        "bank_code": None,
        "confidence": 0,
    }

    if ifsc is None or str(ifsc).strip() == "":

        result["status"] = "MISSING"
        result["message"] = "IFSC code is not provided."
        result["confidence"] = 0

        return result

    value = str(ifsc).strip().upper()

    result["value"] = value

    pattern = r"[A-Z]{4}0[A-Z0-9]{6}"

    if re.fullmatch(pattern, value):

        result["status"] = "VALID"
        result["bank_code"] = value[:4]
        result["confidence"] = 90
        result["message"] = (
            f"Valid IFSC format — "
            f"Bank code: {value[:4]}."
        )

    else:

        if len(value) != 11:
            result["message"] = (
                f"IFSC must be 11 characters, "
                f"got {len(value)}."
            )
        elif value[4] != "0":
            result["message"] = (
                "5th character of IFSC must be '0'."
            )
        else:
            result["message"] = (
                "Invalid IFSC format."
            )

        result["confidence"] = 15

    return result


# ============================================================
# AMOUNT VALIDATION
# ============================================================

def validate_amount(
    amount: Any,
    field_label: str = "Amount",
    min_value: float = 0,
    max_value: float = None,
) -> Dict[str, Any]:
    """Validate a monetary amount."""

    result = {
        "field": field_label,
        "value": None,
        "status": "INVALID",
        "message": "",
        "confidence": 0,
    }

    if amount is None:

        result["status"] = "MISSING"
        result["message"] = (
            f"{field_label} is not provided."
        )

        return result

    try:

        numeric = float(str(amount))

    except (ValueError, TypeError):

        result["message"] = (
            f"{field_label} must be a number."
        )
        result["confidence"] = 10

        return result

    result["value"] = numeric

    if numeric < min_value:

        result["message"] = (
            f"{field_label} must be at least "
            f"Rs.{min_value:,.2f}."
        )
        result["confidence"] = 20

        return result

    if max_value is not None and numeric > max_value:

        result["message"] = (
            f"{field_label} exceeds maximum "
            f"allowed value of Rs.{max_value:,.2f}."
        )
        result["confidence"] = 20

        return result

    result["status"] = "VALID"
    result["confidence"] = 90
    result["message"] = (
        f"{field_label}: Rs.{numeric:,.2f} "
        "is within valid range."
    )

    return result


# ============================================================
# DATE VALIDATION
# ============================================================

def validate_date_sanity(
    date_value: Any,
    field_label: str = "Date",
    allow_future: bool = False,
) -> Dict[str, Any]:
    """
    Validate date for sanity.

    Checks:
    - Not in the distant past (before 1900)
    - Not in the future (unless allowed)
    """

    from datetime import date, datetime

    result = {
        "field": field_label,
        "value": None,
        "status": "INVALID",
        "message": "",
        "confidence": 0,
    }

    if date_value is None:

        result["status"] = "MISSING"
        result["message"] = (
            f"{field_label} is not provided."
        )

        return result

    # Convert to date object
    if isinstance(date_value, datetime):
        d = date_value.date()
    elif isinstance(date_value, date):
        d = date_value
    else:

        result["message"] = (
            f"{field_label} is not a valid date."
        )
        result["confidence"] = 10

        return result

    result["value"] = str(d)

    today = date.today()

    if d.year < 1900:

        result["message"] = (
            f"{field_label} year {d.year} seems "
            "unreasonable."
        )
        result["confidence"] = 10

        return result

    if not allow_future and d > today:

        result["message"] = (
            f"{field_label} is set to a future "
            f"date ({d})."
        )
        result["confidence"] = 30

        return result

    result["status"] = "VALID"
    result["confidence"] = 90
    result["message"] = (
        f"{field_label}: {d} is valid."
    )

    return result
