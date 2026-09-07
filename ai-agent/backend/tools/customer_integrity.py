from database import get_connection


def check_customer_series():
    connection = get_connection()
    cursor = connection.cursor()

    try:
        cursor.execute(
            """
            SELECT customer_id
            FROM customer
            ORDER BY customer_id
            """
        )

        rows = cursor.fetchall()

        ids = [int(row[0]) for row in rows]

        if not ids:
            return {
                "success": True,
                "intent": "CHECK_CUSTOMER_SERIES",
                "valid": True,
                "message": "No customers found."
            }

        duplicates = []
        seen = set()

        for customer_id in ids:
            if customer_id in seen:
                duplicates.append(customer_id)

            seen.add(customer_id)

        expected = set(range(min(ids), max(ids) + 1))
        actual = set(ids)

        missing = sorted(expected - actual)

        return {
            "success": True,
            "intent": "CHECK_CUSTOMER_SERIES",
            "valid": len(duplicates) == 0 and len(missing) == 0,
            "total_customers": len(ids),
            "first_customer_id": min(ids),
            "last_customer_id": max(ids),
            "missing_ids": missing,
            "duplicate_ids": sorted(set(duplicates))
        }

    finally:
        cursor.close()
        connection.close()


def customer_status_summary():
    connection = get_connection()
    cursor = connection.cursor(dictionary=True)

    try:
        cursor.execute(
            """
            SELECT
                UPPER(status) AS status,
                COUNT(*) AS count
            FROM customer
            GROUP BY UPPER(status)
            ORDER BY status
            """
        )

        rows = cursor.fetchall()

        return {
            "success": True,
            "intent": "CUSTOMER_STATUS_SUMMARY",
            "statuses": rows
        }

    finally:
        cursor.close()
        connection.close()