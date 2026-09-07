import os
import mysql.connector

from config import (
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME
)


def get_connection():

    return mysql.connector.connect(
        host=os.getenv("DB_HOST", DB_HOST),
        port=int(os.getenv("DB_PORT", DB_PORT)),
        user=os.getenv("DB_USER", DB_USER),
        password=os.getenv("DB_PASSWORD", DB_PASSWORD),
        database=os.getenv("DB_NAME", DB_NAME),
        autocommit=True
    )


def fetch_one(sql, params=()):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )

        cursor.execute(
            sql,
            params
        )

        return cursor.fetchone()

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def fetch_all(sql, params=()):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
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

        if connection:
            connection.close()


def fetch_value(sql, params=()):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor()

        cursor.execute(
            sql,
            params
        )

        row = cursor.fetchone()

        if row:
            return row[0]

        return None

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def table_exists(table_name):

    value = fetch_value(
        """
        SELECT COUNT(*)
        FROM information_schema.TABLES
        WHERE TABLE_SCHEMA=%s
        AND TABLE_NAME=%s
        """,
        (
            DB_NAME,
            table_name
        )
    )

    return value > 0


def get_columns(table_name):

    rows = fetch_all(
        """
        SELECT COLUMN_NAME
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA=%s
        AND TABLE_NAME=%s
        ORDER BY ORDINAL_POSITION
        """,
        (
            DB_NAME,
            table_name
        )
    )

    return [
        row["COLUMN_NAME"]
        for row in rows
    ]


def safe_identifier(name):

    return "`" + str(name).replace(
        "`",
        "``"
    ) + "`"