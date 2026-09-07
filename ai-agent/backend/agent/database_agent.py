# backend/agent/database_agent.py

import os
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache

import mysql.connector
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "eshakara")


# ============================================================
# COLUMN CANDIDATES
# ============================================================

DATE_COLUMNS = [
    "created_at",
    "created_on",
    "created_date",
    "creation_date",

    "onboarded_at",
    "onboarding_at",
    "onboarding_date",

    "opened_at",
    "opening_at",
    "opening_date",

    "account_created_at",
    "account_opened_at",

    "transaction_date",
    "transaction_datetime",
    "transacted_at",

    "deposit_date",
    "deposit_datetime",

    "date_created",
    "datetime_created",

    "timestamp",
    "date",
    "datetime",
]


CUSTOMER_ID_COLUMNS = [
    "customer_id",
    "cust_id",
    "customer_no",
    "user_id",
    "member_id",
]


NAME_COLUMNS = [
    "customer_name",
    "cust_name",
    "customer",
    "name",
]


ACCOUNT_COLUMNS = [
    "account_no",
    "account_number",
    "ac_no",
    "a_c_no",
]


AMOUNT_COLUMNS = [
    "transaction_amount",
    "amount",
    "deposit_amount",
    "credit_amount",
    "debit_amount",
]


TRANSACTION_TYPE_COLUMNS = [
    "transaction_type",
    "type",
    "entry_type",
]


PAYMENT_MODE_COLUMNS = [
    "mode_of_pay",
    "payment_mode",
    "mode",
]


DESCRIPTION_COLUMNS = [
    "description",
    "remarks",
    "narration",
]


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():

    return mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True,
        connection_timeout=5,
    )


# ============================================================
# IDENTIFIER SAFETY
# ============================================================

def quote_identifier(name: str) -> str:

    return "`" + name.replace("`", "``") + "`"


# ============================================================
# TABLE/COLUMN CACHE
# ============================================================

_TABLE_CACHE = {}


def get_table_columns(table: str):

    table_lower = table.lower()

    if table_lower in _TABLE_CACHE:
        return _TABLE_CACHE[table_lower]

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            """
            SELECT COLUMN_NAME
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (DB_NAME, table),
        )

        columns = [row[0] for row in cursor.fetchall()]

        _TABLE_CACHE[table_lower] = columns

        return columns

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def table_exists(table: str) -> bool:

    try:
        return bool(get_table_columns(table))
    except Exception:
        return False


def find_column(columns, candidates):

    lookup = {
        str(column).lower(): column
        for column in columns
    }

    for candidate in candidates:

        if candidate.lower() in lookup:
            return lookup[candidate.lower()]

    return None


# ============================================================
# DATE/TIME
# ============================================================

def get_date_range(period):

    now = datetime.now()

    today = datetime(
        now.year,
        now.month,
        now.day,
    )

    if period == "today":
        return today, today + timedelta(days=1)

    if period == "yesterday":
        return (
            today - timedelta(days=1),
            today,
        )

    if period == "tomorrow":
        return (
            today + timedelta(days=1),
            today + timedelta(days=2),
        )

    if period == "this_week":

        start = today - timedelta(
            days=today.weekday()
        )

        return start, start + timedelta(days=7)

    if period == "last_week":

        start = today - timedelta(
            days=today.weekday()
        )

        return (
            start - timedelta(days=7),
            start,
        )

    if period == "this_month":

        start = datetime(
            today.year,
            today.month,
            1,
        )

        if today.month == 12:

            end = datetime(
                today.year + 1,
                1,
                1,
            )

        else:

            end = datetime(
                today.year,
                today.month + 1,
                1,
            )

        return start, end

    if period == "last_month":

        current_month = datetime(
            today.year,
            today.month,
            1,
        )

        previous = current_month - timedelta(days=1)

        start = datetime(
            previous.year,
            previous.month,
            1,
        )

        return start, current_month

    if period == "this_year":

        return (
            datetime(today.year, 1, 1),
            datetime(today.year + 1, 1, 1),
        )

    if period == "last_year":

        return (
            datetime(today.year - 1, 1, 1),
            datetime(today.year, 1, 1),
        )

    return None


def format_datetime(value):

    if value is None:
        return "Not available"

    if isinstance(value, datetime):

        return value.strftime(
            "%d %B %Y at %I:%M %p"
        )

    return str(value)


# ============================================================
# CUSTOMER
# ============================================================

def get_customer(customer_id):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            """
            SELECT *
            FROM `customer`
            WHERE `customer_id` = %s
            LIMIT 1
            """,
            (customer_id,),
        )

        return cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def get_customer_count():

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM `customer`"
        )

        return int(cursor.fetchone()[0])

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def get_customers_by_period(period):

    columns = get_table_columns("customer")

    date_column = find_column(
        columns,
        DATE_COLUMNS,
    )

    if not date_column:
        raise RuntimeError(
            "The customer table does not contain a creation/onboarding date column."
        )

    start, end = get_date_range(period)

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        sql = f"""
            SELECT *
            FROM `customer`
            WHERE {quote_identifier(date_column)} >= %s
              AND {quote_identifier(date_column)} < %s
            ORDER BY {quote_identifier(date_column)} DESC
        """

        cursor.execute(
            sql,
            (start, end),
        )

        return cursor.fetchall(), date_column

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# CUSTOMER NAME
# ============================================================

def get_customer_name(customer):

    if not customer:
        return None

    first = str(
        customer.get("first_name") or ""
    ).strip()

    last = str(
        customer.get("last_name") or ""
    ).strip()

    name = f"{first} {last}".strip()

    return name or None


# ============================================================
# TRANSACTION DATE COLUMN
# ============================================================

def transaction_columns():

    return get_table_columns(
        "fd_transactions"
    )


def transaction_date_column():

    columns = transaction_columns()

    return find_column(
        columns,
        DATE_COLUMNS,
    )


# ============================================================
# TRANSACTIONS
# ============================================================

def get_transactions(
    customer_id=None,
    period=None,
    limit=500,
):

    if not table_exists("fd_transactions"):
        return [], None

    columns = transaction_columns()

    date_column = find_column(
        columns,
        DATE_COLUMNS,
    )

    id_column = find_column(
        columns,
        CUSTOMER_ID_COLUMNS,
    )

    name_column = find_column(
        columns,
        NAME_COLUMNS,
    )

    conditions = []
    params = []

    # --------------------------------------------------------
    # DATE FILTER
    # --------------------------------------------------------

    if period and date_column:

        date_range = get_date_range(period)

        if date_range:

            start, end = date_range

            conditions.append(
                f"{quote_identifier(date_column)} >= %s"
            )

            conditions.append(
                f"{quote_identifier(date_column)} < %s"
            )

            params.extend([
                start,
                end,
            ])

    # --------------------------------------------------------
    # CUSTOMER FILTER
    # --------------------------------------------------------

    customer_name = None

    if customer_id is not None:

        if id_column:

            conditions.append(
                f"{quote_identifier(id_column)} = %s"
            )

            params.append(customer_id)

        elif name_column:

            customer = get_customer(
                customer_id
            )

            customer_name = get_customer_name(
                customer
            )

            if customer_name:

                conditions.append(
                    f"LOWER(TRIM({quote_identifier(name_column)})) = LOWER(TRIM(%s))"
                )

                params.append(
                    customer_name
                )

    # --------------------------------------------------------
    # SQL
    # --------------------------------------------------------

    sql = "SELECT * FROM `fd_transactions`"

    if conditions:

        sql += " WHERE " + " AND ".join(
            conditions
        )

    if date_column:

        sql += (
            f" ORDER BY "
            f"{quote_identifier(date_column)} DESC"
        )

    sql += f" LIMIT {int(limit)}"

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            tuple(params),
        )

        return cursor.fetchall(), date_column

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# TRANSACTION COUNT
# ============================================================

def get_transaction_count(
    customer_id=None,
    period=None,
):

    rows, _ = get_transactions(
        customer_id=customer_id,
        period=period,
        limit=5000,
    )

    return len(rows)


# ============================================================
# TRANSACTION TOTAL
# ============================================================

def get_transaction_total(
    customer_id=None,
    period=None,
):

    rows, _ = get_transactions(
        customer_id=customer_id,
        period=period,
        limit=5000,
    )

    total = Decimal("0")

    for row in rows:

        amount_column = find_column(
            list(row.keys()),
            AMOUNT_COLUMNS,
        )

        if not amount_column:
            continue

        value = row.get(amount_column)

        if value is None:
            continue

        try:

            total += Decimal(
                str(value)
            )

        except Exception:
            pass

    return total, len(rows)


# ============================================================
# PRODUCT RECORDS
# ============================================================

def get_product_records(
    table,
    customer_id=None,
    period=None,
    limit=500,
):

    if not table_exists(table):
        return [], None

    columns = get_table_columns(table)

    date_column = find_column(
        columns,
        DATE_COLUMNS,
    )

    id_column = find_column(
        columns,
        CUSTOMER_ID_COLUMNS,
    )

    conditions = []
    params = []

    if period and date_column:

        start, end = get_date_range(
            period
        )

        conditions.append(
            f"{quote_identifier(date_column)} >= %s"
        )

        conditions.append(
            f"{quote_identifier(date_column)} < %s"
        )

        params.extend([
            start,
            end,
        ])

    if customer_id is not None and id_column:

        conditions.append(
            f"{quote_identifier(id_column)} = %s"
        )

        params.append(customer_id)

    sql = (
        f"SELECT * FROM "
        f"{quote_identifier(table)}"
    )

    if conditions:

        sql += (
            " WHERE "
            + " AND ".join(conditions)
        )

    if date_column:

        sql += (
            " ORDER BY "
            + quote_identifier(date_column)
            + " DESC"
        )

    sql += f" LIMIT {int(limit)}"

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            tuple(params),
        )

        return cursor.fetchall(), date_column

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SCHEMA HEALTH
# ============================================================

def database_health():

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute("SELECT 1")

        cursor.fetchone()

        tables = {}

        for table in [
            "customer",
            "fd_transactions",
            "fd",
            "rd",
            "share_account",
        ]:

            try:

                tables[table] = (
                    get_table_columns(table)
                )

            except Exception:

                tables[table] = []

        return {
            "database": "connected",
            "tables": tables,
        }

    except Exception as exc:

        return {
            "database": "disconnected",
            "error": str(exc),
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


# ============================================================
# SCHEMES INTELLIGENCE
# ============================================================

def get_fd_schemes():
    """Query distinct FD schemes and their DB field statistics."""
    sql = """
        SELECT 
            scheme_name,
            COUNT(*) as account_count,
            MIN(fd_amount) as min_deposit,
            MAX(fd_amount) as max_deposit,
            AVG(fd_amount) as avg_deposit,
            SUM(fd_amount) as total_deposit_volume
        FROM fd
        GROUP BY scheme_name
        ORDER BY account_count DESC, scheme_name ASC
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_rd_schemes():
    """Query distinct RD tenure schemes and their DB field statistics."""
    sql = """
        SELECT 
            tenure,
            COUNT(*) as account_count,
            MIN(principal_amount) as min_installment,
            MAX(principal_amount) as max_installment,
            SUM(principal_amount) as total_monthly_inflow,
            MIN(maturity_amount) as min_maturity,
            MAX(maturity_amount) as max_maturity
        FROM rd
        GROUP BY tenure
        ORDER BY tenure ASC
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


def get_share_schemes():
    """Query Share capital statistics."""
    sql = """
        SELECT 
            COUNT(*) as account_count,
            SUM(total_shares) as total_shares,
            MIN(share_amount) as min_amount,
            MAX(share_amount) as max_amount,
            SUM(share_amount) as total_share_capital
        FROM share_account
    """
    connection = None
    cursor = None
    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute(sql)
        return cursor.fetchall()
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()