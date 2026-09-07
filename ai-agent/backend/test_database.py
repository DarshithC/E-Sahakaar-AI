from database import get_connection


try:
    connection = get_connection()

    print("MYSQL CONNECTION: SUCCESS")

    cursor = connection.cursor()

    cursor.execute("SELECT DATABASE()")

    result = cursor.fetchone()

    print("DATABASE:", result[0])

    cursor.execute(
        "SELECT COUNT(*) FROM customer"
    )

    result = cursor.fetchone()

    print("CUSTOMER COUNT:", result[0])

    cursor.close()
    connection.close()

except Exception as e:

    print("MYSQL CONNECTION FAILED")
    print(e)