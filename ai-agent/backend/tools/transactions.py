from database import get_connection


# ============================================================
# GET TRANSACTIONS BY FD ACCOUNT
# ============================================================

def get_transactions_by_account(account_no):

    connection = None
    cursor = None

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                transaction_id,
                transaction_date,
                account_no,
                customer_name,
                description,
                transaction_amount,
                transaction_type,
                mode_of_pay
            FROM fd_transactions
            WHERE account_no = %s
            ORDER BY transaction_date DESC
            """,
            (account_no,)
        )

        transactions = cursor.fetchall()

        return {
            "success": True,
            "account_no": account_no,
            "count": len(transactions),
            "transactions": transactions
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


# ============================================================
# GET CUSTOMER FD TRANSACTIONS
# ============================================================

def get_customer_transactions(customer_id):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                t.transaction_id,
                t.transaction_date,
                t.account_no,
                t.customer_name,
                t.description,
                t.transaction_amount,
                t.transaction_type,
                t.mode_of_pay
            FROM fd_transactions t
            INNER JOIN fd f
                ON t.account_no = f.account_no
            WHERE f.customer_id = %s
            ORDER BY t.transaction_date DESC
            """,
            (customer_id,)
        )

        transactions = cursor.fetchall()

        return {
            "success": True,
            "customer_id": customer_id,
            "count": len(transactions),
            "transactions": transactions
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


# ============================================================
# VERIFY FD DEPOSIT
# ============================================================

def verify_fd_deposit(account_no):

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(dictionary=True)

        # ----------------------------------------------------
        # Get FD account
        # ----------------------------------------------------

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

        fd_account = cursor.fetchone()

        if not fd_account:

            return {
                "success": False,
                "verified": False,
                "message": "FD account not found."
            }

        expected_amount = float(
            fd_account["fd_amount"] or 0
        )

        # ----------------------------------------------------
        # Get transactions
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                transaction_id,
                transaction_date,
                account_no,
                customer_name,
                description,
                transaction_amount,
                transaction_type,
                mode_of_pay
            FROM fd_transactions
            WHERE account_no = %s
            ORDER BY transaction_date ASC
            """,
            (account_no,)
        )

        transactions = cursor.fetchall()

        # ----------------------------------------------------
        # Find FD opening/deposit transaction
        # ----------------------------------------------------

        opening_transaction = None

        for transaction in transactions:

            description = str(
                transaction.get("description") or ""
            ).lower()

            transaction_type = str(
                transaction.get("transaction_type") or ""
            ).lower()

            amount = float(
                transaction.get("transaction_amount") or 0
            )

            is_credit = transaction_type == "credit"

            is_fd_opening = (
                "fd account opening" in description
                or "fd opening" in description
                or "deposit" in description
                or "fd deposit" in description
            )

            if is_credit and is_fd_opening:

                opening_transaction = transaction
                break

        # ----------------------------------------------------
        # If no obvious opening transaction, search for
        # matching credit amount
        # ----------------------------------------------------

        if opening_transaction is None:

            for transaction in transactions:

                transaction_type = str(
                    transaction.get("transaction_type") or ""
                ).lower()

                amount = float(
                    transaction.get("transaction_amount") or 0
                )

                if (
                    transaction_type == "credit"
                    and abs(amount - expected_amount) < 0.01
                ):

                    opening_transaction = transaction
                    break

        # ----------------------------------------------------
        # No matching transaction
        # ----------------------------------------------------

        if opening_transaction is None:

            return {
                "success": True,
                "verified": False,
                "account_no": account_no,
                "customer_id": fd_account["customer_id"],
                "expected_fd_amount": expected_amount,
                "transaction_found": False,
                "message": (
                    "FD account exists, but no matching "
                    "deposit transaction was found."
                ),
                "fd_account": fd_account,
                "transactions": transactions
            }

        # ----------------------------------------------------
        # Compare amounts
        # ----------------------------------------------------

        actual_amount = float(
            opening_transaction["transaction_amount"] or 0
        )

        difference = round(
            actual_amount - expected_amount,
            2
        )

        verified = abs(difference) < 0.01

        # ----------------------------------------------------
        # Final result
        # ----------------------------------------------------

        if verified:

            message = (
                "FD deposit verification successful. "
                f"Expected amount ₹{expected_amount:.2f} "
                f"and matching transaction amount "
                f"₹{actual_amount:.2f} were found."
            )

        else:

            message = (
                "FD deposit mismatch detected. "
                f"Expected ₹{expected_amount:.2f}, "
                f"but transaction shows "
                f"₹{actual_amount:.2f}. "
                f"Difference: ₹{difference:.2f}."
            )

        return {
            "success": True,
            "verified": verified,
            "account_no": account_no,
            "customer_id": fd_account["customer_id"],
            "expected_fd_amount": expected_amount,
            "actual_transaction_amount": actual_amount,
            "difference": difference,
            "transaction_found": True,
            "transaction": opening_transaction,
            "fd_account": fd_account,
            "message": message
        }

    except Exception as e:

        return {
            "success": False,
            "verified": False,
            "error": str(e)
        }

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()