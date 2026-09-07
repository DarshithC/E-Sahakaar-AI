import re

from database import get_connection


# ============================================================
# VALIDATION HELPERS
# ============================================================

def is_valid_phone(phone):
    """
    Validate Indian 10-digit mobile number.
    """

    if phone is None:
        return False

    phone = str(phone).strip()

    return bool(
        re.fullmatch(r"[6-9][0-9]{9}", phone)
    )


def is_valid_pan(pan):
    """
    Validate PAN format.

    Example:
    ABCDE1234F
    """

    if pan is None:
        return False

    pan = str(pan).strip().upper()

    return bool(
        re.fullmatch(
            r"[A-Z]{5}[0-9]{4}[A-Z]",
            pan
        )
    )


def is_valid_aadhaar(aadhaar):
    """
    Validate Aadhaar.

    Supports both:

    123412341234

    and masked format such as:

    XXXX XXXX 1001
    """

    if aadhaar is None:
        return False

    aadhaar = str(aadhaar).strip()

    # Completely numeric Aadhaar
    if re.fullmatch(r"[0-9]{12}", aadhaar):
        return True

    # Masked Aadhaar used in your database
    if re.fullmatch(
        r"X{4}\sX{4}\s[0-9]{4}",
        aadhaar,
        re.IGNORECASE
    ):
        return True

    return False


def is_filled(value):
    """
    Check whether a required field contains data.
    """

    if value is None:
        return False

    return bool(str(value).strip())


# ============================================================
# CUSTOMER VALIDATION
# ============================================================

def validate_customer(customer_id: int):

    result = {
        "success": False,
        "customer_id": customer_id,
        "overall_status": "INVALID",
        "checks": [],
        "errors": [],
        "warnings": []
    }

    # --------------------------------------------------------
    # Validate customer ID input
    # --------------------------------------------------------

    if customer_id is None:

        result["errors"].append(
            "Customer ID was not provided."
        )

        return result

    try:
        customer_id = int(customer_id)

    except (TypeError, ValueError):

        result["errors"].append(
            "Customer ID must be a number."
        )

        return result


    if customer_id <= 0:

        result["errors"].append(
            "Customer ID must be greater than zero."
        )

        return result


    # --------------------------------------------------------
    # Database connection
    # --------------------------------------------------------

    connection = None
    cursor = None

    try:

        connection = get_connection()

        cursor = connection.cursor(
            dictionary=True
        )


        # ====================================================
        # 1. GET CUSTOMER
        # ====================================================

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


        if not customer:

            result["errors"].append(
                f"Customer ID {customer_id} does not exist."
            )

            result["checks"].append({
                "check": "Customer existence",
                "status": "FAIL",
                "message": "Customer not found."
            })

            return result


        result["success"] = True

        result["customer"] = {
            "customer_id": customer["customer_id"],
            "name": (
                f"{customer.get('first_name', '')} "
                f"{customer.get('last_name', '')}"
            ).strip(),
            "status": customer.get("status")
        }


        # ====================================================
        # 2. CUSTOMER ID
        # ====================================================

        result["checks"].append({
            "check": "Customer ID",
            "status": "PASS",
            "message": f"Customer ID {customer_id} exists."
        })


        # ====================================================
        # 3. REQUIRED FIELDS
        # ====================================================

        required_fields = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "relation_name": "Relation Name",
            "phone_no": "Phone Number",
            "gender": "Gender",
            "residential_address": "Residential Address",
            "aadhaar_no": "Aadhaar Number",
            "pan_no": "PAN Number",
            "status": "Status"
        }

        missing_fields = []

        for field, display_name in required_fields.items():

            if not is_filled(customer.get(field)):

                missing_fields.append(
                    display_name
                )


        if missing_fields:

            result["checks"].append({
                "check": "Required fields",
                "status": "FAIL",
                "message": (
                    "Missing fields: "
                    + ", ".join(missing_fields)
                )
            })

            result["errors"].append(
                "Required customer fields are missing."
            )

        else:

            result["checks"].append({
                "check": "Required fields",
                "status": "PASS",
                "message": "All required customer fields are filled."
            })


        # ====================================================
        # 4. PHONE NUMBER
        # ====================================================

        phone = customer.get("phone_no")

        if is_valid_phone(phone):

            result["checks"].append({
                "check": "Phone Number",
                "status": "PASS",
                "message": "Phone number format is valid."
            })

        else:

            result["checks"].append({
                "check": "Phone Number",
                "status": "FAIL",
                "message": "Phone number format is invalid."
            })

            result["errors"].append(
                "Invalid phone number."
            )


        # ====================================================
        # 5. AADHAAR
        # ====================================================

        aadhaar = customer.get("aadhaar_no")

        if is_valid_aadhaar(aadhaar):

            result["checks"].append({
                "check": "Aadhaar",
                "status": "PASS",
                "message": "Aadhaar format is valid."
            })

        else:

            result["checks"].append({
                "check": "Aadhaar",
                "status": "FAIL",
                "message": "Aadhaar format is invalid or missing."
            })

            result["errors"].append(
                "Invalid Aadhaar number."
            )


        # ====================================================
        # 6. PAN
        # ====================================================

        pan = customer.get("pan_no")

        if is_valid_pan(pan):

            result["checks"].append({
                "check": "PAN",
                "status": "PASS",
                "message": "PAN format is valid."
            })

        else:

            result["checks"].append({
                "check": "PAN",
                "status": "FAIL",
                "message": "PAN format is invalid or missing."
            })

            result["errors"].append(
                "Invalid PAN number."
            )


        # ====================================================
        # 7. DUPLICATE AADHAAR
        # ====================================================

        if is_filled(aadhaar):

            cursor.execute(
                """
                SELECT COUNT(*) AS duplicate_count
                FROM customer
                WHERE aadhaar_no = %s
                AND customer_id <> %s
                """,
                (
                    aadhaar,
                    customer_id
                )
            )

            duplicate_aadhaar = cursor.fetchone()

            count = duplicate_aadhaar["duplicate_count"]


            if count > 0:

                result["checks"].append({
                    "check": "Duplicate Aadhaar",
                    "status": "FAIL",
                    "message": (
                        f"Aadhaar appears in "
                        f"{count} other customer record(s)."
                    )
                })

                result["errors"].append(
                    "Duplicate Aadhaar detected."
                )

            else:

                result["checks"].append({
                    "check": "Duplicate Aadhaar",
                    "status": "PASS",
                    "message": "No duplicate Aadhaar found."
                })


        # ====================================================
        # 8. DUPLICATE PAN
        # ====================================================

        if is_filled(pan):

            cursor.execute(
                """
                SELECT COUNT(*) AS duplicate_count
                FROM customer
                WHERE pan_no = %s
                AND customer_id <> %s
                """,
                (
                    pan,
                    customer_id
                )
            )

            duplicate_pan = cursor.fetchone()

            count = duplicate_pan["duplicate_count"]


            if count > 0:

                result["checks"].append({
                    "check": "Duplicate PAN",
                    "status": "FAIL",
                    "message": (
                        f"PAN appears in "
                        f"{count} other customer record(s)."
                    )
                })

                result["errors"].append(
                    "Duplicate PAN detected."
                )

            else:

                result["checks"].append({
                    "check": "Duplicate PAN",
                    "status": "PASS",
                    "message": "No duplicate PAN found."
                })


        # ====================================================
        # 9. CUSTOMER STATUS
        # ====================================================

        status = customer.get("status")

        if status:

            status_upper = str(status).strip().upper()

            if status_upper in (
                "ACTIVE",
                "APPROVED"
            ):

                result["checks"].append({
                    "check": "Customer Approval",
                    "status": "PASS",
                    "message": (
                        f"Customer status is {status_upper}."
                    )
                })

            elif status_upper in (
                "PENDING",
                "PENDING APPROVAL",
                "APPROVAL PENDING"
            ):

                result["checks"].append({
                    "check": "Customer Approval",
                    "status": "WARNING",
                    "message": (
                        "Customer approval is still pending."
                    )
                })

                result["warnings"].append(
                    "Customer approval is pending."
                )

            elif status_upper in (
                "REJECTED",
                "INACTIVE",
                "BLOCKED"
            ):

                result["checks"].append({
                    "check": "Customer Approval",
                    "status": "FAIL",
                    "message": (
                        f"Customer status is {status_upper}."
                    )
                })

                result["errors"].append(
                    f"Customer status is {status_upper}."
                )

            else:

                result["checks"].append({
                    "check": "Customer Approval",
                    "status": "WARNING",
                    "message": (
                        f"Unrecognized customer status: "
                        f"{status_upper}"
                    )
                })

                result["warnings"].append(
                    "Customer status is not recognized."
                )


        # ====================================================
        # 10. OVERALL RESULT
        # ====================================================

        has_failure = any(
            check["status"] == "FAIL"
            for check in result["checks"]
        )

        has_warning = any(
            check["status"] == "WARNING"
            for check in result["checks"]
        )


        if has_failure:

            result["overall_status"] = "INVALID"

        elif has_warning:

            result["overall_status"] = "PENDING"

        else:

            result["overall_status"] = "VALID"


        return result


    except Exception as e:

        result["success"] = False

        result["errors"].append(
            f"Validation error: {str(e)}"
        )

        return result


    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()