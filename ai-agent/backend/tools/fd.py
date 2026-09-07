from database import get_connection


def get_fd_by_customer(customer_id):
    """
    Get all FD accounts belonging to a customer.
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
                scheme_name,
                account_open_date,
                fd_amount,
                maturity_date,
                maturity_amount,
                status
            FROM fd
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


def validate_fd_account(account_no):
    """
    Validate whether an FD account exists and is active.
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
                scheme_name,
                account_open_date,
                fd_amount,
                maturity_date,
                maturity_amount,
                status
            FROM fd
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
                "message": "FD account not found."
            }

        status = str(account["status"]).upper()

        return {
            "success": True,
            "valid": status == "ACTIVE",
            "account": account,
            "message": (
                "FD account is active."
                if status == "ACTIVE"
                else f"FD account status is {status}."
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