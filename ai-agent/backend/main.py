import os
import re
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional

import mysql.connector
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "readonly_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "")

AGENT_API_KEY = os.getenv(
    "AGENT_API_KEY",
    "E-Sahakara-Agent-2026"
)

VALIDATION_CONFIDENCE_THRESHOLD = int(
    os.getenv("VALIDATION_CONFIDENCE_THRESHOLD", "70")
)

ANOMALY_SENSITIVITY = os.getenv(
    "ANOMALY_SENSITIVITY",
    "medium"
).lower()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="E-Sahakara AI Agent",
    version="11.0"
)


# ============================================================
# AI MODEL INITIALIZATION
# ============================================================

@app.on_event("startup")
def startup_init_ai_model():
    """
    Initialize the custom AI model on server startup.
    Trains the anomaly detector from the database.
    """

    print("\n[AI MODEL] Initializing custom AI engine...")

    try:

        from database import fetch_all, fetch_one
        from ai_model.cbs_validator import (
            set_database_functions,
        )

        from ai_model.anomaly_detector import (
            initialize_detector,
        )

        # Give the validator access to the DB
        set_database_functions(
            fetch_all=fetch_all,
            fetch_one=fetch_one,
        )

        # Train the anomaly detector from DB
        initialize_detector(
            fetch_all_func=fetch_all,
            sensitivity=ANOMALY_SENSITIVITY,
        )

        print("[AI MODEL] ✅ Custom AI engine ready.")
        print("[AI MODEL] No Ollama dependency. Zero external AI.")

    except Exception as exc:

        print(
            f"[AI MODEL] ⚠️ Initialization warning: "
            f"{repr(exc)}"
        )
        print(
            "[AI MODEL] Rule-based validation is "
            "still available."
        )


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://127.0.0.1:5501",
        "http://localhost:5500",
        "http://localhost:5501",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# REQUEST MODEL
# ============================================================

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


# ============================================================
# SESSION MEMORY
# ============================================================

SESSIONS: Dict[str, Dict[str, Any]] = {}


def get_session(
    session_id: Optional[str]
):

    sid = session_id or str(uuid.uuid4())

    if sid not in SESSIONS:

        SESSIONS[sid] = {
            "history": [],
            "last_intent": None,
            "last_customer_id": None,
            "last_period": None,
            "last_validation_scope": None,
            "last_created_rows": [],
            "last_transaction_scope": None,
            "last_product": None,
        }

    return sid, SESSIONS[sid]


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(text: str) -> str:

    text = (text or "").strip().lower()

    replacements = {
        "aaddhar": "aadhaar",
        "aadhar": "aadhaar",
        "adhar": "aadhaar",
        "adhaar": "aadhaar",

        "pan card": "pan",

        "phone number": "phone",
        "mobile number": "phone",
        "mobile no": "phone",
        "phone no": "phone",

        "on boarded": "onboarded",
        "on board": "onboarded",
        "onboarding": "onboarded",

        "registered": "created",
        "registration": "created",
        "joined": "created",
        "account opened": "created",
        "account created": "created",
        "customer added": "created",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# ============================================================
# DATABASE
# ============================================================

def get_db():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
    )


def query_db(
    sql: str,
    params: tuple = ()
) -> List[Dict[str, Any]]:

    conn = None
    cursor = None

    try:

        conn = get_db()

        cursor = conn.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            params
        )

        return cursor.fetchall()

    finally:

        if cursor:
            cursor.close()

        if conn:
            conn.close()


def execute_one(
    sql: str,
    params: tuple = ()
):

    rows = query_db(
        sql,
        params
    )

    return rows[0] if rows else None


# ============================================================
# SCHEMA HELPERS
# ============================================================

_SCHEMA_CACHE: Dict[str, List[str]] = {}

ALLOWED_TABLES = {
    "customer",
    "fd",
    "rd",
    "share_account",
    "fd_transactions",
}


def table_columns(
    table: str
) -> List[str]:

    if table not in ALLOWED_TABLES:
        return []

    if table in _SCHEMA_CACHE:
        return _SCHEMA_CACHE[table]

    rows = query_db(
        """
        SELECT COLUMN_NAME
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ORDINAL_POSITION
        """,
        (
            DB_NAME,
            table
        )
    )

    columns = [
        row["COLUMN_NAME"]
        for row in rows
    ]

    _SCHEMA_CACHE[table] = columns

    return columns


def first_column(
    columns: List[str],
    candidates: List[str]
) -> Optional[str]:

    lower_map = {
        column.lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in lower_map:
            return lower_map[
                candidate.lower()
            ]

    return None


# ============================================================
# CUSTOMER ID
# ============================================================

def get_customer_id(
    text: str
) -> Optional[int]:

    patterns = [

        r"(?:customer|user|member|client)"
        r"\s*(?:id|no|number)?"
        r"\s*[:#-]?\s*(\d+)",

        r"\bcustomer\s+(\d+)",

        r"\buser\s+(\d+)",

        r"\bmember\s+(\d+)",

        r"\bclient\s+(\d+)",
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.I
        )

        if match:
            return int(
                match.group(1)
            )

    return None


# ============================================================
# CUSTOMER DATA
# ============================================================

def get_customer(
    customer_id: int
):

    return execute_one(
        """
        SELECT
            customer_id,
            first_name,
            last_name,
            relation_name,
            phone_no,
            gender,
            residential_address,
            caste,
            aadhaar_no,
            pan_no,
            status,
            created_at
        FROM customer
        WHERE customer_id = %s
        """,
        (
            customer_id,
        )
    )


def get_all_customers():

    return query_db(
        """
        SELECT
            customer_id,
            first_name,
            last_name,
            relation_name,
            phone_no,
            gender,
            residential_address,
            caste,
            aadhaar_no,
            pan_no,
            status,
            created_at
        FROM customer
        ORDER BY customer_id
        """
    )


# ============================================================
# MASKING
# ============================================================

def mask_aadhaar(
    value: Any
) -> str:

    if value is None:
        return "Not available"

    value = str(value)

    if "x" in value.lower():
        return value

    digits = re.sub(
        r"\D",
        "",
        value
    )

    if len(digits) >= 4:

        return (
            "XXXX XXXX "
            + digits[-4:]
        )

    return value


def mask_pan(
    value: Any
) -> str:

    if value is None:
        return "Not available"

    value = str(value)

    if len(value) >= 4:

        return (
            value[:2]
            + "XXXXX"
            + value[-2:]
        )

    return value


# ============================================================
# CUSTOMER FORMAT
# ============================================================

def format_customer(
    row: Dict[str, Any]
) -> str:

    name = (
        f"{row.get('first_name', '')} "
        f"{row.get('last_name', '')}"
    ).strip()

    created_raw = row.get("created_at")
    created_str = format_transaction_date(created_raw) if created_raw else "Not available"

    return (
        f"Member Profile — {name}\n"
        f"• Member ID: {row.get('customer_id') or 'N/A'}\n"
        f"• Account Holder Name: {name or 'N/A'}\n"
        f"• Father / Guardian Name (C/o): {row.get('relation_name') or 'N/A'}\n"
        f"• Registered Mobile Number: {row.get('phone_no') or 'N/A'}\n"
        f"• Gender: {row.get('gender') or 'N/A'}\n"
        f"• Residential Address: {row.get('residential_address') or 'N/A'}\n"
        f"• Social Category: {row.get('caste') or 'General'}\n"
        f"• PAN Card Number: {mask_pan(row.get('pan_no'))}\n"
        f"• Aadhaar Number (UIDAI): {mask_aadhaar(row.get('aadhaar_no'))}\n"
        f"• Membership Status: {row.get('status') or 'ACTIVE'}\n"
        f"• Member Registration Date: {created_str}"
    )


# ============================================================
# PERIOD
# ============================================================

def detect_period(
    text: str
) -> Optional[str]:

    if "today" in text:
        return "today"

    if "yesterday" in text:
        return "yesterday"

    if "tomorrow" in text:
        return "tomorrow"

    if "this week" in text:
        return "this_week"

    if "last week" in text:
        return "last_week"

    if "this month" in text:
        return "this_month"

    if "last month" in text:
        return "last_month"

    if "this year" in text:
        return "this_year"

    if "last year" in text:
        return "last_year"

    return None


def period_range(
    period: str
):

    today = date.today()

    if period == "today":

        return (
            today,
            today + timedelta(days=1)
        )

    if period == "yesterday":

        start = today - timedelta(days=1)

        return (
            start,
            today
        )

    if period == "tomorrow":

        start = today + timedelta(days=1)

        return (
            start,
            start + timedelta(days=1)
        )

    if period == "this_week":

        start = (
            today
            - timedelta(
                days=today.weekday()
            )
        )

        return (
            start,
            start + timedelta(days=7)
        )

    if period == "last_week":

        end = (
            today
            - timedelta(
                days=today.weekday()
            )
        )

        start = end - timedelta(days=7)

        return (
            start,
            end
        )

    if period == "this_month":

        start = today.replace(day=1)

        if start.month == 12:

            end = date(
                start.year + 1,
                1,
                1
            )

        else:

            end = date(
                start.year,
                start.month + 1,
                1
            )

        return (
            start,
            end
        )

    if period == "last_month":

        first_this_month = today.replace(
            day=1
        )

        last_month_end = first_this_month

        if first_this_month.month == 1:

            last_month_start = date(
                first_this_month.year - 1,
                12,
                1
            )

        else:

            last_month_start = date(
                first_this_month.year,
                first_this_month.month - 1,
                1
            )

        return (
            last_month_start,
            last_month_end
        )

    if period == "this_year":

        start = date(
            today.year,
            1,
            1
        )

        return (
            start,
            date(
                today.year + 1,
                1,
                1
            )
        )

    if period == "last_year":

        start = date(
            today.year - 1,
            1,
            1
        )

        return (
            start,
            date(
                today.year,
                1,
                1
            )
        )

    return None, None


# ============================================================
# CUSTOMER CREATION
# ============================================================

def customers_by_period(
    period: str
):

    start, end = period_range(
        period
    )

    if not start:
        return []

    return query_db(
        """
        SELECT
            customer_id,
            first_name,
            last_name,
            relation_name,
            phone_no,
            gender,
            residential_address,
            caste,
            aadhaar_no,
            pan_no,
            status,
            created_at
        FROM customer
        WHERE created_at >= %s
          AND created_at < %s
        ORDER BY created_at
        """,
        (
            start,
            end
        )
    )


def creation_answer(
    period: str,
    session: Dict[str, Any]
):

    rows = customers_by_period(
        period
    )

    session["last_created_rows"] = rows
    session["last_period"] = period
    session["last_intent"] = "CUSTOMER_CREATION"

    label = {
        "today": "today",
        "yesterday": "yesterday",
        "tomorrow": "tomorrow",
        "this_week": "this week",
        "last_week": "last week",
        "this_month": "this month",
        "last_month": "last month",
        "this_year": "this year",
        "last_year": "last year",
    }.get(
        period,
        period
    )

    if not rows:

        return (
            f"No customers were created "
            f"{label}."
        )

    return (
        f"{len(rows)} customer(s) were "
        f"created {label}."
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_pan(
    pan: Any
) -> str:

    if not pan:
        return "NOT AVAILABLE"

    value = str(
        pan
    ).strip().upper()

    if len(value) != 10:
        return "INVALID"

    if re.fullmatch(
        r"[A-Z]{5}[0-9]{4}[A-Z]",
        value
    ):

        return "VALID"

    return "INVALID"


def validate_aadhaar(
    aadhaar: Any
) -> str:

    if not aadhaar:
        return "NOT AVAILABLE"

    value = str(
        aadhaar
    ).strip()

    if "x" in value.lower():
        return "PARTIALLY VERIFIABLE"

    digits = re.sub(
        r"\D",
        "",
        value
    )

    if len(digits) == 12:
        return "VALID FORMAT"

    return "INVALID"


def validate_customer(
    row
):

    return {
        "customer_id":
            row["customer_id"],

        "name":
            (
                f"{row.get('first_name', '')} "
                f"{row.get('last_name', '')}"
            ).strip(),

        "pan":
            validate_pan(
                row.get("pan_no")
            ),

        "aadhaar":
            validate_aadhaar(
                row.get("aadhaar_no")
            ),
    }


# ============================================================
# VALIDATION ANSWER
# ============================================================

def validation_answer(
    text: str,
    session: Dict[str, Any]
):

    all_users = any(
        phrase in text
        for phrase in [
            "all users",
            "all the users",
            "all customers",
            "all the customers",
            "all members",
            "every user",
            "every customer",
            "each user",
            "each customer",
            "of all the users",
            "of all users",
            "of all the customers",
            "of all customers",
            "in bulk",
            "bulk",
            "everyone",
            "invalid data",
            "invalid users",
            "invalid customers",
            "defective",
            "how many users",
            "which users",
            "who has invalid",
        ]
    ) or (not customer_id and any(w in text.lower() for w in ["invalid", "defect", "defective", "audit"]))

    customer_id = get_customer_id(
        text
    )

    previous_created_rows = (
        session.get(
            "last_created_rows",
            []
        )
    )

    previous_creation_context = (
        session.get("last_intent")
        == "CUSTOMER_CREATION"
    )

    contextual_reference = any(
        phrase in text
        for phrase in [
            "that user",
            "that customer",
            "this user",
            "this customer",
            "those users",
            "those customers",
            "these users",
            "these customers",
            "the user",
            "the customer",
            "the users",
            "the customers",
            "their pan",
            "their aadhaar",
            "their pan and aadhaar",
            "his pan",
            "his aadhaar",
            "her pan",
            "her aadhaar",
            "their",
            "them",
        ]
    )

    # --------------------------------------------------------
    # PREVIOUS ONBOARDING RESULT
    # --------------------------------------------------------

    if (
        not customer_id
        and not all_users
        and previous_creation_context
        and contextual_reference
        and previous_created_rows
    ):

        results = []

        for row in previous_created_rows:
            cid = row.get("customer_id")
            try:
                from ai_model.cbs_validator import validate_customer_full
                full_rep = validate_customer_full(cid)
                if full_rep.get("success"):
                    results.append(full_rep.get("report"))
                    continue
            except Exception:
                pass

            result = validate_customer(row)
            results.append(
                f"• Member #{result['customer_id']} ({result['name']}):\n"
                f"  - PAN Card: {result['pan']}\n"
                f"  - Aadhaar (UIDAI): {result['aadhaar']}"
            )

        session["last_intent"] = "VALIDATION"
        session["last_validation_scope"] = "LAST_CREATED"

        if len(previous_created_rows) == 1:
            session["last_customer_id"] = previous_created_rows[0]["customer_id"]

        return (
            f"Validation Results for Recently Onboarded Member(s):\n\n"
            + "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n".join(results)
        )

    # --------------------------------------------------------
    # ALL USERS — Custom AI Validation Engine
    # --------------------------------------------------------

    if all_users:

        try:
            from ai_model.cbs_validator import validate_all_customers

            report_data = validate_all_customers()
            session["last_intent"] = "VALIDATION"
            session["last_validation_scope"] = "ALL"
            session["last_customer_id"] = None

            return report_data.get("report", "No validation report generated.")

        except Exception as exc:
            print(f"[CBS BULK VALIDATION ERROR] {repr(exc)}")

        # Fallback to basic validation
        rows = get_all_customers()

        if not rows:

            return (
                "There are no customers "
                "in the database."
            )

        invalid = []
        partially = []

        for row in rows:

            result = validate_customer(
                row
            )

            if (
                result["pan"] == "INVALID"
                or
                result["aadhaar"] == "INVALID"
            ):

                invalid.append(result)

            elif (
                result["pan"] != "VALID"
                or
                result["aadhaar"]
                != "VALID FORMAT"
            ):

                partially.append(result)

        session["last_intent"] = "VALIDATION"
        session["last_validation_scope"] = "ALL"
        session["last_customer_id"] = None

        lines = [
            f"I have reviewed all {len(rows)} customer accounts in the CBS database.",
            "",
        ]

        if invalid:

            lines.append(
                f"Here are the member records that require your attention ({len(invalid)} member(s)):\n"
            )

            for item in invalid:
                issues = []
                if item.get("pan") == "INVALID":
                    issues.append("PAN Card Number: The PAN card format is invalid. A valid PAN card requires 10 alphanumeric characters (5 letters, 4 digits, 1 letter).")
                if item.get("aadhaar") == "INVALID":
                    issues.append("Aadhaar Number (UIDAI): The Aadhaar number is invalid. A valid Aadhaar requires 12 numeric digits.")
                issues_text = "\n    • ".join(issues) if issues else "Document verification failed."

                lines.append(
                    f"Member #{item['customer_id']} — {item['name']}:\n"
                    f"    • {issues_text}\n"
                    f"    • Action needed: Please collect valid identity proofs and update in the CBS system.\n"
                )

        else:

            lines.append(
                "All customer PAN and Aadhaar identity formats are valid with no defects found."
            )

        if partially:

            lines.append(
                "Note: Some Aadhaar numbers are stored in masked format, so their full 12 digits cannot be independently verified."
            )

        return "\n".join(lines)

    # --------------------------------------------------------
    # SPECIFIC CUSTOMER — Custom AI Validation Engine
    # --------------------------------------------------------

    if customer_id:

        try:
            from ai_model.cbs_validator import validate_customer_full

            report_data = validate_customer_full(customer_id)

            if report_data.get("success"):
                session["last_intent"] = "VALIDATION"
                session["last_customer_id"] = customer_id
                session["last_validation_scope"] = "CUSTOMER"

                return report_data.get("report", "Validation report generated.")

        except Exception as exc:
            print(f"[CBS CUSTOMER VALIDATION ERROR] {repr(exc)}")

        # Fallback to basic validation
        row = get_customer(
            customer_id
        )

        if not row:

            return (
                f"Customer {customer_id} "
                "was not found."
            )

        result = validate_customer(
            row
        )

        session["last_intent"] = "VALIDATION"
        session["last_customer_id"] = customer_id
        session["last_validation_scope"] = (
            "CUSTOMER"
        )

        return (
            f"Validation result for "
            f"customer {customer_id} "
            f"({result['name']}):\n\n"

            f"PAN: {result['pan']}\n"

            f"Aadhaar: {result['aadhaar']}"
        )

    return (
        "Please provide a customer ID, "
        "or say \"validate PAN and Aadhaar "
        "of all users\"."
    )


# ============================================================
# DATE / MONEY FORMATTING
# ============================================================

def format_transaction_date(
    value: Any
) -> str:

    if value is None:
        return "Date not available"

    if isinstance(value, datetime):

        return value.strftime(
            "%d %B %Y, %I:%M %p"
        ).lstrip("0")

    if isinstance(value, date):

        return value.strftime(
            "%d %B %Y"
        ).lstrip("0")

    return str(value)


def format_money(
    value: Any
) -> str:

    if value is None:
        return "₹0.00"

    try:

        amount = Decimal(
            str(value)
        )

        return (
            "₹"
            + format(
                amount,
                ",.2f"
            )
        )

    except Exception:

        return f"₹{value}"


# ============================================================
# TRANSACTION HUMAN-READABLE FORMAT
# ============================================================

def format_transaction(
    row: Dict[str, Any],
    number: int
) -> str:

    transaction_date = (
        row.get("transaction_date")
        or
        row.get("date")
        or
        row.get("created_at")
    )

    account_no = (
        row.get("account_no")
        or
        row.get("account_number")
        or
        row.get("account")
        or
        "N/A"
    )

    customer_name = (
        row.get("customer_name")
        or
        "N/A"
    )

    description = (
        row.get("description")
        or
        "N/A"
    )

    amount = (
        row.get("transaction_amount")
        if
        row.get("transaction_amount")
        is not None
        else
        row.get("amount")
    )

    raw_type = str(row.get("transaction_type") or row.get("type") or "N/A").upper()
    if raw_type in ("DEPOSIT", "CREDIT"):
        type_str = "Deposit (Credit)"
    elif raw_type in ("WITHDRAWAL", "DEBIT"):
        type_str = "Withdrawal (Debit)"
    else:
        type_str = row.get("transaction_type") or row.get("type") or "N/A"

    payment_mode = (
        row.get("mode_of_pay")
        or
        row.get("payment_mode")
        or
        row.get("mode")
        or
        "N/A"
    )

    return (
        f"Transaction #{number} | Date: {format_transaction_date(transaction_date)}\n"
        f"   • Account Number: {account_no}\n"
        f"   • Customer Name: {customer_name}\n"
        f"   • Amount Transacted: {format_money(amount)}\n"
        f"   • Transaction Type: {type_str}\n"
        f"   • Payment Channel: {payment_mode}\n"
        f"   • Remarks / Narration: {description}"
    )


# ============================================================
# TRANSACTION DATA
# ============================================================

def transaction_rows(
    customer_id: Optional[int] = None,
    period: Optional[str] = None
):

    columns = table_columns(
        "fd_transactions"
    )

    if not columns:
        return []

    date_col = first_column(
        columns,
        [
            "transaction_date",
            "created_at",
            "date",
        ]
    )

    customer_id_col = first_column(
        columns,
        [
            "customer_id",
            "cust_id",
        ]
    )

    if not date_col:

        date_col = "transaction_date"

    sql = """
        SELECT *
        FROM fd_transactions
    """

    conditions = []

    params = []

    if customer_id:

        if customer_id_col:

            conditions.append(
                f"`{customer_id_col}` = %s"
            )

            params.append(
                customer_id
            )

        else:

            customer = get_customer(
                customer_id
            )

            if not customer:
                return []

            full_name = (
                f"{customer.get('first_name', '')} "
                f"{customer.get('last_name', '')}"
            ).strip()

            if "customer_name" in columns:

                conditions.append(
                    "`customer_name` = %s"
                )

                params.append(
                    full_name
                )

    if period:

        start, end = period_range(
            period
        )

        if start:

            conditions.append(
                f"`{date_col}` >= %s"
            )

            params.append(start)

            conditions.append(
                f"`{date_col}` < %s"
            )

            params.append(end)

    if conditions:

        sql += (
            " WHERE "
            +
            " AND ".join(
                conditions
            )
        )

    sql += (
        f" ORDER BY `{date_col}` DESC"
    )

    return query_db(
        sql,
        tuple(params)
    )


# ============================================================
# TRANSACTION SUMMARY
# ============================================================

def transaction_summary(
    customer_id: Optional[int] = None,
    period: Optional[str] = None
):

    rows = transaction_rows(
        customer_id,
        period
    )

    amount_field = None

    if rows:

        amount_field = first_column(
            list(rows[0].keys()),
            [
                "transaction_amount",
                "amount",
                "deposit_amount",
            ]
        )

    total = Decimal("0.00")

    if amount_field:

        for row in rows:

            try:

                total += Decimal(
                    str(
                        row.get(
                            amount_field
                        ) or 0
                    )
                )

            except Exception:
                pass

    return (
        len(rows),
        total
    )


# ============================================================
# HUMAN-READABLE TRANSACTION ANSWER
# ============================================================

def transaction_answer(
    text: str,
    session: Dict[str, Any]
):

    customer_id = get_customer_id(
        text
    )

    all_scope = any(
        phrase in text
        for phrase in [
            "all customers",
            "all users",
            "every customer",
            "every user",
            "overall",
            "all",
        ]
    )

    period = detect_period(
        text
    )

    # Follow-up:
    #
    # transaction of customer 3
    # yesterday
    #
    # Keeps customer 3.
    if (
        not customer_id
        and not all_scope
        and period
        and session.get("last_intent")
        == "TRANSACTIONS"
    ):

        customer_id = session.get(
            "last_transaction_scope"
        )

    # Explicit all scope overrides
    # previous customer scope.
    if all_scope:

        customer_id = None

    rows = transaction_rows(
        customer_id,
        period
    )

    session["last_intent"] = (
        "TRANSACTIONS"
    )

    session["last_customer_id"] = (
        customer_id
    )

    session["last_transaction_scope"] = (
        customer_id
    )

    session["last_period"] = period

    # --------------------------------------------------------
    # CUSTOMER NAME
    # --------------------------------------------------------

    customer_name = None

    if customer_id:

        customer = get_customer(
            customer_id
        )

        if not customer:

            return (
                f"Customer {customer_id} "
                "was not found."
            )

        customer_name = (
            f"{customer.get('first_name', '')} "
            f"{customer.get('last_name', '')}"
        ).strip()

    # --------------------------------------------------------
    # SCOPE
    # --------------------------------------------------------

    if customer_id:

        scope_text = (
            f"Customer {customer_id}"
        )

        if customer_name:

            scope_text += (
                f" ({customer_name})"
            )

    else:

        scope_text = "all customers"

    # --------------------------------------------------------
    # PERIOD
    # --------------------------------------------------------

    if period:

        period_text = (
            period.replace(
                "_",
                " "
            )
        )

        period_text = (
            " for "
            + period_text
        )

    else:

        period_text = ""

    # --------------------------------------------------------
    # NO TRANSACTIONS
    # --------------------------------------------------------

    if not rows:

        return (
            f"No transactions were found "
            f"for {scope_text}"
            f"{period_text}."
        )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    amount_field = first_column(
        list(rows[0].keys()),
        [
            "transaction_amount",
            "amount",
            "deposit_amount",
        ]
    )

    total_amount = Decimal(
        "0.00"
    )

    if amount_field:

        for row in rows:

            try:

                total_amount += Decimal(
                    str(
                        row.get(
                            amount_field
                        ) or 0
                    )
                )

            except Exception:
                pass

    # --------------------------------------------------------
    # HUMAN-READABLE RESPONSE
    # --------------------------------------------------------

    lines = [

        f"I found {len(rows)} "
        f"transaction"
        f"{'s' if len(rows) != 1 else ''} "
        f"for {scope_text}"
        f"{period_text}.",

        ""
    ]

    for index, row in enumerate(
        rows,
        start=1
    ):

        lines.append(
            format_transaction(
                row,
                index
            )
        )

        lines.append("")

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    if amount_field:

        lines.append(
            f"Total transaction amount: "
            f"{format_money(total_amount)}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# PRODUCT ANSWER
# ============================================================

def product_answer(
    text: str,
    product: str,
    session: Dict[str, Any]
):

    table = product

    columns = table_columns(
        table
    )

    if not columns:

        return (
            f"I couldn't find the "
            f"{product} table in the "
            "database."
        )

    customer_id = get_customer_id(
        text
    )

    all_scope = any(
        phrase in text
        for phrase in [
            "all customers",
            "all users",
            "every customer",
            "every user",
            "all users",
        ]
    )

    if (
        not customer_id
        and not all_scope
        and session.get("last_intent")
        == product.upper()
    ):

        customer_id = session.get(
            "last_customer_id"
        )

    if all_scope:

        customer_id = None

    conditions = []

    params = []

    id_col = first_column(
        columns,
        [
            "customer_id",
            "cust_id",
            "customerid",
        ]
    )

    date_col = first_column(
        columns,
        [
            "created_at",
            "opening_date",
            "account_opening_date",
            "date",
        ]
    )

    if customer_id:

        if id_col:

            conditions.append(
                f"`{id_col}` = %s"
            )

            params.append(
                customer_id
            )

        else:

            customer = get_customer(
                customer_id
            )

            if (
                customer
                and
                "customer_name"
                in columns
            ):

                name = (
                    f"{customer.get('first_name', '')} "
                    f"{customer.get('last_name', '')}"
                ).strip()

                conditions.append(
                    "`customer_name` = %s"
                )

                params.append(
                    name
                )

    sql = (
        f"SELECT * FROM `{table}`"
    )

    if conditions:

        sql += (
            " WHERE "
            +
            " AND ".join(
                conditions
            )
        )

    if date_col:

        sql += (
            f" ORDER BY `{date_col}` DESC"
        )

    sql += " LIMIT 50"

    rows = query_db(
        sql,
        tuple(params)
    )

    session["last_intent"] = (
        product.upper()
    )

    session["last_product"] = product

    session["last_customer_id"] = (
        customer_id
    )

    if not rows:

        scope = (
            f"customer {customer_id}"
            if customer_id
            else "all customers"
        )

        return (
            f"No {product.upper()} records "
            f"were found for {scope}."
        )

    try:
        from agent.response import product_response
        cust_row = get_customer(customer_id) if customer_id else None
        cust_name = f"{cust_row.get('first_name', '')} {cust_row.get('last_name', '')}".strip() if cust_row else None
        return product_response(rows, product, customer_name=cust_name)
    except Exception as exc:
        print(f"[PRODUCT FORMAT ERROR] {repr(exc)}")

    # Fallback to labeled output
    lines = [
        f"Found {len(rows)} {product.upper()} record(s):",
        ""
    ]

    for idx, row in enumerate(rows, start=1):
        lines.append(f"Account #{idx}:")
        for k, v in row.items():
            friendly = str(k).replace("_", " ").title()
            if "amount" in str(k).lower():
                val_display = format_money(v)
            elif "date" in str(k).lower():
                val_display = format_transaction_date(v)
            else:
                val_display = str(v)
            lines.append(f"  • {friendly}: {val_display}")
        lines.append("")

    return "\n".join(lines)


# ============================================================
# CUSTOMER DETAILS
# ============================================================

def customer_details(
    text: str,
    session: Dict[str, Any]
):

    customer_id = get_customer_id(
        text
    )

    all_scope = any(
        phrase in text
        for phrase in [
            "all customers",
            "all users",
            "all the users",
            "all the customers",
            "every customer",
            "every user",
        ]
    )

    if (
        not customer_id
        and not all_scope
        and session.get("last_intent")
        in [
            "CUSTOMER_COUNT",
            "CUSTOMER_CREATION",
            "CUSTOMER_DETAILS",
        ]
    ):

        previous_rows = session.get(
            "last_created_rows",
            []
        )

        if previous_rows:

            return (
                "\n\n".join(
                    format_customer(row)
                    for row in previous_rows
                )
            )

        all_scope = True

    if all_scope:

        rows = get_all_customers()

        session["last_intent"] = (
            "CUSTOMER_DETAILS"
        )

        session["last_customer_id"] = None

        if not rows:

            return (
                "There are no customers."
            )

        return (
            f"Customer details for all "
            f"{len(rows)} customers:\n\n"
            +
            "\n\n".join(
                format_customer(row)
                for row in rows
            )
        )

    if customer_id:

        row = get_customer(
            customer_id
        )

        session["last_intent"] = (
            "CUSTOMER_DETAILS"
        )

        session["last_customer_id"] = (
            customer_id
        )

        if not row:

            return (
                f"Customer {customer_id} "
                "was not found."
            )

        return format_customer(
            row
        )

    return (
        "Please provide a customer ID "
        "or say \"give me details for "
        "all users\"."
    )


# ============================================================
# CUSTOMER COUNT
# ============================================================

def customer_count(
    text: str,
    session: Dict[str, Any]
):

    period = detect_period(
        text
    )

    if period:

        rows = customers_by_period(
            period
        )

        session["last_intent"] = (
            "CUSTOMER_CREATION"
        )

        session["last_period"] = period

        session["last_created_rows"] = (
            rows
        )

        return (
            f"There are {len(rows)} "
            f"customer(s) created "
            f"{period.replace('_', ' ')}."
        )

    rows = query_db(
        """
        SELECT COUNT(*) AS total
        FROM customer
        """
    )

    total = rows[0]["total"]

    session["last_intent"] = (
        "CUSTOMER_COUNT"
    )

    session["last_customer_id"] = None

    session["last_created_rows"] = (
        get_all_customers()
    )

    return (
        f"There are currently {total} "
        "customers in the banking database."
    )


# ============================================================
# LOCAL GENERAL CHAT
# ============================================================

def local_chat(
    text: str
) -> Optional[str]:

    t = normalize(
        text
    )

    if re.fullmatch(
        r"(hi|hii|hiii|hello|hey|heyy|heyyy|"
        r"hey there|good morning|good afternoon|"
        r"good evening)[!. ]*",
        t
    ):

        hour = datetime.now().hour

        if hour < 12:
            greeting = "Good morning"

        elif hour < 17:
            greeting = "Good afternoon"

        else:
            greeting = "Good evening"

        return (
            f"{greeting}! I'm E-Sahakara AI. "
            "How can I help you today?"
        )

    if any(
        phrase in t
        for phrase in [
            "how are you",
            "how r u",
            "how are u",
            "how are you doing",
            "are you doing well",
            "are you okay",
        ]
    ):

        return (
            "I'm doing great, thank you! "
            "I'm ready to help with banking "
            "data, customer details, "
            "transactions, FD, RD, share "
            "accounts, and validations."
        )

    if any(
        phrase in t
        for phrase in [
            "what's up",
            "whats up",
            "what is up",
        ]
    ):

        return (
            "I'm here and ready to help! "
            "You can ask me about customers, "
            "transactions, accounts, or "
            "validations."
        )

    if any(
        phrase in t
        for phrase in [
            "thank you",
            "thanks",
            "thank u",
            "thx",
        ]
    ):

        return (
            "You're welcome! Let me know "
            "if you need anything else."
        )

    if re.fullmatch(
        r"(bye|goodbye|see you|see ya|take care)[!. ]*",
        t
    ):

        return (
            "Goodbye! Have a great day."
        )

    if any(
        phrase in t
        for phrase in [
            "who are you",
            "what are you",
            "tell me about yourself",
        ]
    ):

        return (
            "I'm E-Sahakara AI, a local "
            "banking assistant. I can retrieve "
            "and validate banking information "
            "from the connected database and "
            "handle general questions using "
            "the local AI model."
        )

    if t in [
        "help",
        "what can you do",
        "what can you help with",
    ]:

        return (
            "I can help with:\n"
            "• Customer information\n"
            "• Customer onboarding/creation\n"
            "• Transactions\n"
            "• FD, RD and share accounts\n"
            "• PAN/Aadhaar validation\n"
            "• Banking-related general questions"
        )

    return None


# ============================================================
# CUSTOM AI RESPONSE ENGINE
# ============================================================

def ai_response(
    user_message: str,
    session: Dict[str, Any]
) -> str:
    """
    Generate a response using the custom AI engine.
    Replaces Ollama completely.
    """

    from ai_model.response_engine import (
        generate_response,
    )

    return generate_response(
        user_message,
        session,
    )


# ============================================================
# INTENT DETECTION
# ============================================================

def detect_intent(
    text: str,
    session: Dict[str, Any]
) -> str:

    t = normalize(
        text
    )

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    if (
        "validate" in t
        or "validation" in t
        or "valid pan" in t
        or "valid aadhaar" in t
        or "invalid pan" in t
        or "invalid aadhaar" in t
        or "pan valid" in t
        or "aadhaar valid" in t
        or "pan or aadhaar" in t
        or "pan and aadhaar" in t
        or "invalid" in t
        or "defect" in t
        or "defective" in t
        or "audit" in t
    ):

        return "VALIDATION"

    # --------------------------------------------------------
    # VALIDATION CONTEXT
    # --------------------------------------------------------

    if session.get(
        "last_intent"
    ) in [
        "CUSTOMER_CREATION",
        "VALIDATION",
    ]:

        previous_created_rows = (
            session.get(
                "last_created_rows",
                []
            )
        )

        if previous_created_rows:

            contextual_reference = any(
                phrase in t
                for phrase in [
                    "that user",
                    "that customer",
                    "this user",
                    "this customer",
                    "those users",
                    "those customers",
                    "these users",
                    "these customers",
                    "the user",
                    "the customer",
                    "their pan",
                    "their aadhaar",
                    "their pan and aadhaar",
                    "his pan",
                    "his aadhaar",
                    "her pan",
                    "her aadhaar",
                    "their",
                    "them",
                ]
            )

            if contextual_reference:

                if (
                    "pan" in t
                    or
                    "aadhaar" in t
                    or
                    "validate" in t
                    or
                    "validation" in t
                    or
                    "valid" in t
                    or
                    "invalid" in t
                ):

                    return "VALIDATION"

    # --------------------------------------------------------
    # EXPLICIT ENTITY FLAGS
    # --------------------------------------------------------

    is_fd = bool(re.search(r"\b(fd|fixed deposit|fixed deposits)\b", t))
    is_rd = bool(re.search(r"\b(rd|recurring deposit|recurring deposits)\b", t))
    is_share = bool(re.search(r"\b(share|shares|share account|share accounts|shared account|share capital)\b", t))

    is_explicit_txn = any(
        word in t
        for word in [
            "transaction",
            "transactions",
            "txns",
            "deposit transaction",
            "withdrawal",
            "withdrawals",
            "transaction amount",
            "transaction count",
            "transfers",
            "banking activity",
        ]
    )

    is_scheme_query = any(
        w in t for w in [
            "scheme", "schemes", "plan", "plans", "type of", "types of", 
            "different fd", "different rd", "what are the fd", "what are the rd",
            "what fd", "what rd", "list fd", "list rd", "available fd", "available rd",
            "how many types", "deposit options", "deposit types"
        ]
    ) or ("how many" in t and ("fd" in t or "rd" in t or "scheme" in t) and "customer" not in t and "account" not in t and "user" not in t)

    # --------------------------------------------------------
    # SCHEMES / PRODUCT TYPES INQUIRY
    # --------------------------------------------------------

    if is_scheme_query:
        if is_rd and not is_fd:
            return "RD_SCHEMES"
        elif is_share and not is_fd and not is_rd:
            return "SHARE_SCHEMES"
        elif is_fd and not is_rd:
            return "FD_SCHEMES"
        else:
            return "ALL_SCHEMES"

    # --------------------------------------------------------
    # PRODUCTS: FD / RD / SHARE (when not explicit transactions)
    # --------------------------------------------------------

    if is_fd and not is_explicit_txn:
        return "FD"

    if is_rd and not is_explicit_txn:
        return "RD"

    if is_share and not is_explicit_txn:
        return "SHARE"

    # --------------------------------------------------------
    # CUSTOMER CREATION
    # --------------------------------------------------------

    if (
        "created" in t
        or "onboarded" in t
        or "onboard" in t
        or "new customers" in t
        or "new users" in t
        or "joined" in t
    ):

        if any(
            phrase in t
            for phrase in [
                "how many",
                "count",
                "number of",
                "give me",
                "show me",
                "details",
            ]
        ):

            return "CUSTOMER_CREATION"

    # --------------------------------------------------------
    # CUSTOMER COUNT
    # --------------------------------------------------------

    if not any(w in t for w in ["invalid", "defect", "defective", "error", "issue", "wrong", "fake", "audit"]):
        if any(
            phrase in t
            for phrase in [
                "how many users",
                "how many customers",
                "number of users",
                "number of customers",
                "customer count",
                "user count",
                "total customers",
                "total users",
            ]
        ):

            return "CUSTOMER_COUNT"

    # --------------------------------------------------------
    # CUSTOMER DETAILS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "customer details",
            "customer information",
            "user details",
            "user information",
            "member details",
            "member information",
            "details of customer",
            "details for customer",
            "details of user",
            "details for user",
        ]
    ):

        return "CUSTOMER_DETAILS"

    # --------------------------------------------------------
    # TRANSACTIONS
    # --------------------------------------------------------

    if is_explicit_txn:
        return "TRANSACTIONS"

    if (
        session.get("last_intent")
        == "TRANSACTIONS"
    ):
        has_other_entity = (
            is_fd or is_rd or is_share or
            any(w in t for w in ["customer", "customers", "user", "users", "member", "members", "scheme", "schemes", "pan", "aadhaar", "validation", "invalid", "defect", "audit"])
        )
        if not has_other_entity and any(
            phrase in t
            for phrase in [
                "yesterday",
                "today",
                "this month",
                "this year",
                "last month",
                "last year",
                "all customers",
                "all users",
                "overall",
                "more transactions",
                "recent transactions",
            ]
        ):
            return "TRANSACTIONS"

    # --------------------------------------------------------
    # THEIR DETAILS
    # --------------------------------------------------------

    if any(
        phrase in t
        for phrase in [
            "give me their details",
            "show me their details",
            "give their details",
            "show their details",
            "give me the details",
            "show me the details",
            "their details",
            "more details",
        ]
    ):

        if session.get(
            "last_intent"
        ) in [
            "CUSTOMER_COUNT",
            "CUSTOMER_CREATION",
            "CUSTOMER_DETAILS",
        ]:

            return "CUSTOMER_DETAILS"

        if session.get(
            "last_intent"
        ) in [
            "FD",
            "RD",
            "SHARE",
        ]:

            return session[
                "last_intent"
            ]

        if session.get(
            "last_intent"
        ) == "TRANSACTIONS":

            return "TRANSACTIONS"

    return "GENERAL"


# ============================================================
# CHAT ENDPOINT
# ============================================================

@app.post("/api/chat")
def chat(
    request: ChatRequest,
    x_agent_key: Optional[str] = Header(
        default=None
    )
):

    if (
        x_agent_key
        and
        x_agent_key != AGENT_API_KEY
    ):

        raise HTTPException(
            status_code=401,
            detail="Invalid agent key"
        )

    message = request.message.strip()

    if not message:

        return {
            "answer":
                "Please enter a question.",
            "session_id":
                request.session_id
        }

    sid, session = get_session(
        request.session_id
    )

    normalized = normalize(
        message
    )

    # ========================================================
    # LOCAL CHAT FIRST
    # ========================================================

    local_answer = local_chat(
        normalized
    )

    if local_answer:

        answer = local_answer

        session["last_intent"] = (
            "GENERAL"
        )

    else:

        intent = detect_intent(
            normalized,
            session
        )

        try:

            if intent == "CUSTOMER_COUNT":

                answer = customer_count(
                    normalized,
                    session
                )

            elif intent == "CUSTOMER_CREATION":

                period = detect_period(
                    normalized
                )

                if (
                    not period
                    and
                    session.get(
                        "last_intent"
                    )
                    == "CUSTOMER_CREATION"
                ):

                    period = session.get(
                        "last_period"
                    )

                if period:

                    answer = creation_answer(
                        period,
                        session
                    )

                else:

                    answer = customer_count(
                        normalized,
                        session
                    )

            elif intent == "CUSTOMER_DETAILS":

                answer = customer_details(
                    normalized,
                    session
                )

            elif intent == "VALIDATION":

                answer = validation_answer(
                    normalized,
                    session
                )

            elif intent == "TRANSACTIONS":

                # Overall transaction amount
                if (
                    "overall transaction amount"
                    in normalized
                    or
                    (
                        "total transaction amount"
                        in normalized
                        and
                        "customer"
                        not in normalized
                    )
                ):

                    count, total = (
                        transaction_summary()
                    )

                    session[
                        "last_intent"
                    ] = "TRANSACTIONS"

                    session[
                        "last_transaction_scope"
                    ] = None

                    answer = (
                        f"Overall transaction count: "
                        f"{count}\n"
                        f"Overall transaction amount: "
                        f"{format_money(total)}"
                    )

                else:

                    answer = transaction_answer(
                        normalized,
                        session
                    )

            elif intent == "FD_SCHEMES":

                from agent.database_agent import get_fd_schemes
                from agent.response import fd_schemes_response

                answer = fd_schemes_response(get_fd_schemes())
                session["last_intent"] = "FD_SCHEMES"

            elif intent == "RD_SCHEMES":

                from agent.database_agent import get_rd_schemes
                from agent.response import rd_schemes_response

                answer = rd_schemes_response(get_rd_schemes())
                session["last_intent"] = "RD_SCHEMES"

            elif intent in ("ALL_SCHEMES", "SHARE_SCHEMES"):

                from agent.database_agent import get_fd_schemes, get_rd_schemes, get_share_schemes
                from agent.response import all_schemes_response

                answer = all_schemes_response(get_fd_schemes(), get_rd_schemes(), get_share_schemes())
                session["last_intent"] = "ALL_SCHEMES"

            elif intent == "FD":

                answer = product_answer(
                    normalized,
                    "fd",
                    session
                )

            elif intent == "RD":

                answer = product_answer(
                    normalized,
                    "rd",
                    session
                )

            elif intent == "SHARE":

                answer = product_answer(
                    normalized,
                    "share_account",
                    session
                )

            else:

                answer = ai_response(
                    message,
                    session
                )

        except mysql.connector.Error as exc:

            print(
                "MYSQL ERROR:",
                exc
            )

            answer = (
                "I couldn't access the banking "
                "database right now. Please "
                "check that MySQL is running "
                "and the database configuration "
                "is correct."
            )

        except Exception as exc:

            print(
                "AGENT ERROR:",
                exc
            )

            answer = (
                "I couldn't process that "
                "request right now. "
                "Please try asking the "
                "question again."
            )

    # ========================================================
    # SAVE HISTORY
    # ========================================================

    session["history"].append(
        {
            "role": "user",
            "content": message
        }
    )

    session["history"].append(
        {
            "role": "assistant",
            "content": answer
        }
    )

    session["history"] = (
        session["history"][-20:]
    )

    # ========================================================
    # RESPONSE
    # ========================================================

    database_intents = [
        "CUSTOMER_COUNT",
        "CUSTOMER_CREATION",
        "CUSTOMER_DETAILS",
        "VALIDATION",
        "TRANSACTIONS",
        "FD",
        "RD",
        "SHARE",
    ]

    return {
        "answer": answer,
        "session_id": sid,
        "intent": session.get(
            "last_intent"
        ),
        "source": (
            "database"
            if
            session.get(
                "last_intent"
            )
            in database_intents
            else
            "custom_ai"
        )
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    database = False
    ai_model_ready = False

    try:

        rows = query_db(
            "SELECT 1 AS ok"
        )

        database = bool(rows)

    except Exception as exc:

        print(
            "DATABASE HEALTH ERROR:",
            exc
        )

    try:

        from ai_model.anomaly_detector import (
            get_detector,
        )

        detector = get_detector()
        ai_model_ready = True

    except Exception:

        ai_model_ready = False

    return {
        "status": "ok",

        "database": (
            "connected"
            if database
            else "not connected"
        ),

        "ai_engine": (
            "ready (custom model)"
            if ai_model_ready
            else "not initialized"
        ),

        "anomaly_detector": (
            "trained"
            if (
                ai_model_ready
                and detector.is_trained
            )
            else "statistical fallback"
        ),

        "external_ai": "none (zero dependency)",
    }


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "application":
            "E-Sahakara AI",

        "status":
            "running",

        "message":
            "AI banking agent is running."
    }