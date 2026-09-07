from database import get_connection


def get_share_by_customer(customer_id):
    """
    Get share account belonging to a customer.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                account_no,
                customer_id,
                total_shares,
                share_amount,
                account_open_date,
                status,
                account_closed_date
            FROM share_account
            WHERE customer_id = %s
            ORDER BY account_open_date DESC
            """,
            (customer_id,)
        )

        accounts = cursor.fetchall()

        return {
            "success": True,
            "customer_id": customer_id,
            "count": len(accounts),
            "accounts": accounts
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()


def validate_share_account(account_no):
    """
    Validate a share account.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                account_no,
                customer_id,
                total_shares,
                share_amount,
                account_open_date,
                status,
                account_closed_date
            FROM share_account
            WHERE account_no = %s
            """,
            (account_no,)
        )

        account = cursor.fetchone()

        if not account:

            return {
                "success": False,
                "valid": False,
                "account_no": account_no,
                "message": "Share account not found."
            }

        status = str(account["status"]).upper()

        return {
            "success": True,
            "valid": status == "ACTIVE",
            "account": account,
            "message": (
                "Share account is active."
                if status == "ACTIVE"
                else f"Share account status is {status}."
            )
        }

    except Exception as e:

        return {
            "success": False,
            "valid": False,
            "error": str(e)
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()