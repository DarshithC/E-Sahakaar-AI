# backend/rag.py

import re
from typing import Optional, Dict, Any


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text: str) -> str:
    text = (text or "").lower().strip()

    replacements = {
        "aadhar": "aadhaar",
        "txn": "transaction",
        "txns": "transactions",
        "on boarded": "onboarded",
        "on board": "onboard",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(r"[^a-z0-9\s:#/.-]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ============================================================
# CUSTOMER ID
# ============================================================

def extract_customer_id(text: str) -> Optional[int]:

    t = normalize(text)

    patterns = [
        r"\bcustomer\s*(?:id|number|no)?\s*[:#-]?\s*(\d+)\b",
        r"\bcustomer\s+(\d+)\b",
        r"\bcust\s*(?:id|number|no)?\s*[:#-]?\s*(\d+)\b",
        r"\buser\s*(?:id|number|no)?\s*[:#-]?\s*(\d+)\b",
        r"\bmember\s*(?:id|number|no)?\s*[:#-]?\s*(\d+)\b",
        r"\bclient\s*(?:id|number|no)?\s*[:#-]?\s*(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, t)

        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None

    return None


# ============================================================
# DATE PERIOD
# ============================================================

DATE_WORDS = {

    "today": [
        "today",
        "todays",
        "this day",
        "current day",
    ],

    "yesterday": [
        "yesterday",
        "previous day",
    ],

    "tomorrow": [
        "tomorrow",
        "next day",
    ],

    "this_week": [
        "this week",
        "current week",
    ],

    "last_week": [
        "last week",
        "previous week",
    ],

    "this_month": [
        "this month",
        "current month",
    ],

    "last_month": [
        "last month",
        "previous month",
    ],

    "this_year": [
        "this year",
        "current year",
    ],

    "last_year": [
        "last year",
        "previous year",
    ],
}


def detect_date_period(text: str) -> Optional[str]:

    t = normalize(text)

    # Longer expressions first.
    ordered = [
        "this_month",
        "last_month",
        "this_year",
        "last_year",
        "this_week",
        "last_week",
        "today",
        "yesterday",
        "tomorrow",
    ]

    for period in ordered:

        for phrase in DATE_WORDS[period]:

            if phrase in t:
                return period

    return None


# ============================================================
# DATE/TIME QUERY
# ============================================================

def asks_for_date_time(text: str) -> bool:

    t = normalize(text)

    words = [
        "when",
        "what time",
        "what date",
        "date and time",
        "date time",
        "timestamp",
        "timestamps",
        "created",
        "creation",
        "onboarded",
        "onboarding",
        "registered",
        "opened",
        "opening",
        "account created",
        "account creation",
    ]

    return any(word in t for word in words)


# ============================================================
# TRANSACTION DETECTION
# ============================================================

TRANSACTION_WORDS = [
    "transaction",
    "transactions",
    "payment",
    "payments",
    "transfer",
    "transfers",
    "credit",
    "credits",
    "debit",
    "debits",
    "account activity",
    "financial activity",
]


def is_transaction_query(text: str) -> bool:

    t = normalize(text)

    return any(word in t for word in TRANSACTION_WORDS)


def asks_transaction_count(text: str) -> bool:

    t = normalize(text)

    return (
        "how many" in t
        or "count" in t
        or "number of" in t
        or "total number" in t
    ) and is_transaction_query(t)


def asks_transaction_amount(text: str) -> bool:

    t = normalize(text)

    amount_words = [
        "transaction amount",
        "transaction total",
        "total transaction amount",
        "total amount",
        "transaction value",
        "how much",
        "sum of transactions",
        "sum transactions",
    ]

    return (
        is_transaction_query(t)
        and any(word in t for word in amount_words)
    )


# ============================================================
# CUSTOMER DETECTION
# ============================================================

def is_customer_count_query(text: str) -> bool:

    t = normalize(text)

    # Exclude queries asking about invalid data, defects, errors, or audits
    issue_words = [
        "invalid", "defect", "defective", "error", "issue", "wrong", "fake", 
        "duplicate", "anomaly", "anomalies", "suspicious", "risk", "audit"
    ]
    if any(w in t for w in issue_words):
        return False

    patterns = [
        "how many customers",
        "how many users",
        "how many members",
        "total customers",
        "total users",
        "customer count",
        "number of customers",
        "number of users",
    ]

    return any(x in t for x in patterns)


def is_customer_details_query(text: str) -> bool:

    t = normalize(text)

    detail_words = [
        "customer details",
        "customer information",
        "customer profile",
        "customer record",
        "customer particulars",
        "details of customer",
        "information about customer",
        "profile of customer",
        "tell me about customer",
        "show customer",
        "get customer",
        "view customer",
        "find customer",
    ]

    return any(x in t for x in detail_words)


def is_customer_creation_query(text: str) -> bool:

    t = normalize(text)

    words = [
        "onboard",
        "onboarded",
        "onboarding",
        "created",
        "creation",
        "registered",
        "registration",
        "new customer",
        "new customers",
        "joined",
        "added customer",
        "customers created",
        "customers onboarded",
        "accounts opened",
    ]

    return any(x in t for x in words)


# ============================================================
# SCHEME / PRODUCT CATALOGUE DETECTION
# ============================================================

def detect_scheme_query(text: str) -> Optional[str]:
    """
    Detect queries asking about schemes, scheme types, or scheme counts.
    """
    t = normalize(text)

    is_scheme_word = any(
        w in t for w in [
            "scheme", "schemes", "plan", "plans", "type of", "types of", 
            "different fd", "different rd", "what are the fd", "what are the rd",
            "what fd", "what rd", "list fd", "list rd", "available fd", "available rd",
            "how many types", "deposit options", "deposit types"
        ]
    ) or ("how many" in t and ("fd" in t or "rd" in t or "scheme" in t) and "customer" not in t and "account" not in t and "user" not in t)

    if not is_scheme_word:
        return None

    is_fd = "fd" in t or "fixed deposit" in t or "term deposit" in t
    is_rd = "rd" in t or "recurring deposit" in t
    is_share = "share" in t or "shares" in t

    if is_fd and not is_rd:
        return "FD_SCHEMES"
    elif is_rd and not is_fd:
        return "RD_SCHEMES"
    elif is_share:
        return "SHARE_SCHEMES"
    return "ALL_SCHEMES"


# ============================================================
# PRODUCT DETECTION
# ============================================================

def detect_product(text: str) -> Optional[str]:

    t = normalize(text)

    if (
        "fixed deposit" in t
        or re.search(r"\bfd\b", t)
        or "term deposit" in t
    ):
        return "FD"

    if (
        "recurring deposit" in t
        or re.search(r"\brd\b", t)
    ):
        return "RD"

    if (
        "share account" in t
        or "share accounts" in t
        or re.search(r"\bshares?\b", t)
    ):
        return "SHARE"

    return None


# ============================================================
# VALIDATION
# ============================================================

def detect_validation(text: str) -> Optional[str]:

    t = normalize(text)

    # Full CBS validation (new)
    full_validation_phrases = [
        "full validation",
        "full cbs validation",
        "run full validation",
        "complete validation",
        "validate fully",
        "full check",
        "cbs check",
        "cbs validation",
        "validate all fields",
        "detailed validation",
    ]

    if any(phrase in t for phrase in full_validation_phrases):
        return "FULL_CBS_VALIDATION"

    # Risk assessment (new)
    risk_phrases = [
        "risk score",
        "risk assessment",
        "anomaly score",
        "anomaly detection",
        "risk level",
        "how risky",
        "is it suspicious",
        "any anomaly",
        "any anomalies",
    ]

    if any(phrase in t for phrase in risk_phrases):
        return "RISK_ASSESSMENT"

    # Existing validation intents
    if any(w in t for w in ["validate", "validation", "audit", "invalid", "defect", "defective", "kyc issue"]):

        if any(
            phrase in t
            for phrase in [
                "all customers",
                "all the customers",
                "all users",
                "all the users",
                "all members",
                "every user",
                "every customer",
                "bulk",
                "in bulk",
                "everyone",
                "how many",
                "which users",
                "which customers",
                "who has",
                "have invalid",
                "has invalid",
                "with invalid",
                "invalid data",
                "invalid users",
                "invalid customers",
            ]
        ) or (extract_customer_id(t) is None and any(w in t for w in ["user", "customer", "member", "data", "record", "account"])):
            return "VALIDATE_ALL_CUSTOMERS"

        return "FULL_CBS_VALIDATION"

    if "pan" in t and "aadhaar" in t:
        return "IDENTITY_VALIDATION"

    if "pan" in t:
        return "PAN_VALIDATION"

    if "aadhaar" in t:
        return "AADHAAR_VALIDATION"

    return None


# ============================================================
# FOLLOW-UP PHRASES
# ============================================================

def is_details_followup(text: str) -> bool:

    t = normalize(text)

    phrases = [
        "give details",
        "give the details",
        "give me details",
        "give me the details",
        "show details",
        "show the details",
        "show me details",
        "show me the details",
        "give their details",
        "give me their details",
        "give the customer details",
        "show their details",
        "show their information",
        "give their information",
        "give me their information",
        "what are their details",
        "what are the details",
        "tell me their details",
        "tell me about them",
        "show them",
        "show the records",
        "show their records",
        "give their records",
        "give me their records",
        "what are their records",
        "who are they",
    ]

    return any(t == phrase or phrase in t for phrase in phrases)


def is_short_followup(text: str) -> bool:

    t = normalize(text)

    phrases = [
        "this year",
        "last year",
        "this month",
        "last month",
        "this week",
        "last week",
        "today",
        "yesterday",
        "tomorrow",
        "details",
        "the details",
        "show them",
        "show it",
        "what about it",
        "what about them",
        "give more",
        "more details",
    ]

    return (
        len(t.split()) <= 7
        and any(p in t for p in phrases)
    )


# ============================================================
# ALL-CUSTOMER OVERRIDE
# ============================================================

def explicitly_all_customers(text: str) -> bool:

    t = normalize(text)

    phrases = [
        "all customers",
        "all users",
        "all members",
        "everyone",
        "whole database",
        "entire database",
        "for all customers",
        "of all customers",
        "across all customers",
        "overall",
        "overall transaction",
        "overall transactions",
    ]

    return any(p in t for p in phrases)


# ============================================================
# MAIN INTENT CLASSIFIER
# ============================================================

def retrieve_intent(text: str) -> Dict[str, Any]:

    t = normalize(text)

    customer_id = extract_customer_id(t)
    period = detect_date_period(t)

    validation = detect_validation(t)

    if validation:
        return {
            "intent": validation,
            "customer_id": customer_id,
            "date_period": period,
        }

    scheme_intent = detect_scheme_query(t)

    if scheme_intent:
        return {
            "intent": scheme_intent,
            "customer_id": customer_id,
            "date_period": period,
        }

    product = detect_product(t)

    if product:
        return {
            "intent": product,
            "customer_id": customer_id,
            "date_period": period,
        }

    if asks_transaction_amount(t):
        return {
            "intent": "TRANSACTION_AMOUNT",
            "customer_id": customer_id,
            "date_period": period,
        }

    if is_transaction_query(t):

        if asks_transaction_count(t):
            intent = "TRANSACTION_COUNT"
        else:
            intent = "TRANSACTIONS"

        return {
            "intent": intent,
            "customer_id": customer_id,
            "date_period": period,
        }

    if is_customer_count_query(t):

        if period:
            return {
                "intent": "CUSTOMER_CREATION",
                "customer_id": customer_id,
                "date_period": period,
            }

        return {
            "intent": "CUSTOMER_COUNT",
            "customer_id": customer_id,
            "date_period": None,
        }

    if is_customer_details_query(t):

        return {
            "intent": "CUSTOMER_DETAILS",
            "customer_id": customer_id,
            "date_period": period,
        }

    if is_customer_creation_query(t):

        return {
            "intent": "CUSTOMER_CREATION",
            "customer_id": customer_id,
            "date_period": period,
        }

    # Check for simple "customer N" pattern
    # that implies wanting details
    if (
        customer_id is not None
        and len(t.split()) <= 5
        and (
            t.startswith("customer ")
            or t.startswith("user ")
        )
    ):
        return {
            "intent": "CUSTOMER_DETAILS",
            "customer_id": customer_id,
            "date_period": period,
        }

    return {
        "intent": "GENERAL",
        "customer_id": customer_id,
        "date_period": period,
    }