from database import get_connection


def get_rd_by_customer(customer_id):
    """
    Get all RD accounts belonging to a customer.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                rd_account_no,
                customer_id,
                account_open_date,
                principal_amount,
                tenure,
                maturity_date,
                maturity_amount,
                status
            FROM rd
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


def validate_rd_account(account_no):
    """
    Validate whether an RD account exists and is active.
    """

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                rd_account_no,
                customer_id,
                account_open_date,
                principal_amount,
                tenure,
                maturity_date,
                maturity_amount,
                status
            FROM rd
            WHERE rd_account_no = %s
            """,
            (account_no,)
        )

        account = cursor.fetchone()

        if not account:

            return {
                "success": False,
                "valid": False,
                "account_no": account_no,
                "message": "RD account not found."
            }

        status = str(account["status"]).upper()

        return {
            "success": True,
            "valid": status == "ACTIVE",
            "account": account,
            "message": (
                "RD account is active."
                if status == "ACTIVE"
                else f"RD account status is {status}."
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