from database import get_connection


# ============================================================
# GET ONE CUSTOMER
# ============================================================

def get_customer(customer_id: int):

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
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
                status
            FROM customer
            WHERE customer_id = %s
            """,
            (customer_id,)
        )

        customer = cursor.fetchone()

        cursor.close()
        connection.close()

        if not customer:

            return {
                "found": False,
                "customer_id": customer_id,
                "message": "Customer not found."
            }

        return {
            "found": True,
            "customer": customer
        }

    except Exception as e:

        return {
            "found": False,
            "error": str(e)
        }


# ============================================================
# CUSTOMER COUNT
# ============================================================

def get_customer_count():

    try:

        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM customer"
        )

        count = cursor.fetchone()[0]

        cursor.close()
        connection.close()

        return {
            "count": count
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# CUSTOMERS ONBOARDED TODAY
# ============================================================

def get_customers_today():

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                customer_id,
                first_name,
                last_name,
                status
            FROM customer
            WHERE DATE(created_at) = CURDATE()
            ORDER BY customer_id DESC
            """
        )

        customers = cursor.fetchall()

        cursor.close()
        connection.close()

        return {
            "count": len(customers),
            "customers": customers
        }

    except Exception as e:

        return {
            "error": str(e)
        }


# ============================================================
# PENDING CUSTOMER APPROVALS
# ============================================================

def get_pending_customer_approvals():

    try:

        connection = get_connection()
        cursor = connection.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                customer_id,
                first_name,
                last_name,
                phone_no,
                status
            FROM customer
            WHERE UPPER(status) IN
                ('PENDING', 'PENDING APPROVAL', 'APPROVAL PENDING')
            ORDER BY customer_id DESC
            """
        )

        customers = cursor.fetchall()

        cursor.close()
        connection.close()

        return {
            "count": len(customers),
            "customers": customers
        }

    except Exception as e:

        return {
            "error": str(e)
        }