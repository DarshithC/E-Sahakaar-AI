# backend/seed_cbs_demo.py
"""
Seed realistic demo data into esahakara_demo CBS database
so the AI Agent and CBS Validation Engine have live records to query.
"""

import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = "root"
DB_PASSWORD = ""
DB_NAME = os.getenv("DB_NAME", "esahakara_demo")


def seed_demo_data():
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        autocommit=True
    )
    cursor = conn.cursor()
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0")

    print(f"[*] Seeding CBS database '{DB_NAME}'...")

    # 1. Seed tbl_customers
    customers_data = [
        (1, 1, "CUST0001", "2026-09-01", "Mr", "Rahul", "Kumar", "Male", "9876543210", "9876543211", "1990-05-14", "rahul.k@example.com", "XXXX XXXX 1001", "ABCDE1001F", "ACTIVE", "Bangalore, Karnataka", "General", "Suresh Kumar"),
        (2, 1, "CUST0002", "2026-09-02", "Ms", "Priya", "Sharma", "Female", "9876543211", "9876543212", "1994-08-22", "priya.s@example.com", "XXXX XXXX 1002", "ABCDE1002G", "ACTIVE", "Mysore, Karnataka", "OBC", "Ramesh Sharma"),
        (3, 1, "CUST0003", "2026-09-03", "Mr", "Amit", "Patel", "Male", "9876543212", "9876543213", "1988-11-05", "amit.p@example.com", "XXXX XXXX 1003", "ABCDE1003H", "ACTIVE", "Hubli, Karnataka", "General", "Kishore Patel"),
        (4, 1, "CUST0004", "2026-09-04", "Mrs", "Sneha", "Reddy", "Female", "9876543213", "9876543214", "1992-02-18", "sneha.r@example.com", "XXXX XXXX 1004", "ABCDE1004J", "ACTIVE", "Mangalore, Karnataka", "General", "Venkatesh Reddy"),
        (5, 1, "CUST0005", "2026-09-04", "Mr", "Suresh", "Patil", "Male", "9876543214", "9876543215", "1985-07-30", "suresh.p@example.com", "XXXX XXXX 1005", "ABCDE1005K", "ACTIVE", "Belgaum, Karnataka", "OBC", "Anand Patil"),
        (6, 1, "CUST0006", "2026-09-05", "Ms", "Ananya", "Iyer", "Female", "9876543215", "9876543216", "1996-12-10", "ananya.i@example.com", "XXXX XXXX 1006", "ABCDE1006L", "ACTIVE", "Bangalore, Karnataka", "General", "Subramanian Iyer"),
        (7, 1, "CUST0007", "2026-09-06", "Mr", "Vikram", "Singh", "Male", "9876543216", "9876543217", "1983-04-25", "vikram.s@example.com", "XXXX XXXX 1007", "ABCDE1007M", "ACTIVE", "Shimoga, Karnataka", "General", "Balwant Singh")
    ]

    for c in customers_data:
        cursor.execute(
            """
            INSERT INTO tbl_customers
            (cust_id, branch_id, cust_no, cust_reg_date, cust_title, cust_fname, cust_lname,
             cust_gender, cust_ph_no, cust_alt_ph_no, cust_dob, cust_email_id, cust_aadhar,
             cust_pan_no, cust_status, cust_res_address, cust_caste, father_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                cust_fname=VALUES(cust_fname),
                cust_lname=VALUES(cust_lname),
                cust_ph_no=VALUES(cust_ph_no),
                cust_aadhar=VALUES(cust_aadhar),
                cust_pan_no=VALUES(cust_pan_no),
                cust_status=VALUES(cust_status)
            """,
            c
        )
    print(f"  [+] Seeded {len(customers_data)} rows into tbl_customers")

    # 2. Seed tbl_fd_masters (FD Schemes)
    fd_schemes = [
        (1, 1, "FD-01", "Sahakara Fixed Deposit - 1 Year", "2026-01-01", 10000.0, 5000000.0, "Compound"),
        (2, 1, "FD-02", "Sahakara Fixed Deposit - 2 Year", "2026-01-01", 10000.0, 10000000.0, "Compound"),
        (3, 1, "FD-03", "Senior Citizen FD", "2026-01-01", 25000.0, 5000000.0, "Simple")
    ]
    for s in fd_schemes:
        cursor.execute(
            """
            INSERT INTO tbl_fd_masters
            (fd_scheme_id, branch_id, fd_scheme_no, fd_scheme_name, created_date, fd_min_amt, fd_max_amt, interst_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE fd_scheme_name=VALUES(fd_scheme_name)
            """,
            s
        )
    print(f"  [+] Seeded {len(fd_schemes)} rows into tbl_fd_masters")

    # 3. Seed tbl_fd_account
    fd_accounts = [
        (1, 1, "FD0001", "2026-09-02", 1, 6.50, 1, 25000.0),
        (2, 1, "FD0002", "2026-09-03", 1, 6.50, 2, 50000.0),
        (3, 1, "FD0003", "2026-09-03", 2, 7.25, 3, 100000.0),
        (4, 1, "FD0004", "2026-09-04", 3, 7.75, 4, 75000.0),
        (5, 1, "FD0005", "2026-09-05", 1, 6.50, 5, 30000.0),
    ]
    for f in fd_accounts:
        cursor.execute(
            """
            INSERT INTO tbl_fd_account
            (fd_acc_id, branch_id, fd_acc_no, acc_open_date, fd_scheme_id, roi, cust_id, principal_amt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE principal_amt=VALUES(principal_amt)
            """,
            f
        )
    print(f"  [+] Seeded {len(fd_accounts)} rows into tbl_fd_account")

    # 4. Seed tbl_rd_masters (RD Schemes)
    rd_schemes = [
        (1, 1, "RD-01", "12-Month RD Plan", "2026-01-01", 1000.0, 50000.0, 6.00, "Monthly", 365),
        (2, 1, "RD-02", "24-Month RD Plan", "2026-01-01", 1000.0, 100000.0, 6.75, "Monthly", 730),
    ]
    for r in rd_schemes:
        cursor.execute(
            """
            INSERT INTO tbl_rd_masters
            (rd_scheme_id, branch_id, rd_scheme_no, rd_scheme_name, rd_created_date, rd_min_amt, rd_max_amt, rd_interst_rate, rd_maturity_type, rd_maturity_days)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE rd_scheme_name=VALUES(rd_scheme_name)
            """,
            r
        )
    print(f"  [+] Seeded {len(rd_schemes)} rows into tbl_rd_masters")

    # 5. Seed tbl_rd_account
    rd_accounts = [
        (1, 1, "RD0001", 1, "2026-09-02", 1, 24000.0, "ACTIVE"),
        (2, 1, "RD0002", 2, "2026-09-03", 1, 36000.0, "ACTIVE"),
        (3, 1, "RD0003", 3, "2026-09-03", 2, 60000.0, "ACTIVE"),
        (4, 1, "RD0004", 4, "2026-09-04", 2, 48000.0, "ACTIVE"),
        (5, 1, "RD0005", 5, "2026-09-05", 1, 12000.0, "ACTIVE"),
    ]
    for ra in rd_accounts:
        cursor.execute(
            """
            INSERT INTO tbl_rd_account
            (rd_acc_id, branch_id, rd_acc_no, cust_id, acc_open_date, rd_scheme_id, balance, rd_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE balance=VALUES(balance)
            """,
            ra
        )
    print(f"  [+] Seeded {len(rd_accounts)} rows into tbl_rd_account")

    # 6. Seed tbl_share_account_master
    share_masters = [
        (1, 1, "SH-01", "Regular Member Shares", 100.0, "2026-01-01", 1, "ACTIVE")
    ]
    for sm in share_masters:
        cursor.execute(
            """
            INSERT INTO tbl_share_account_master
            (scheme_id, branch_id, scheme_code, scheme_name, share_amount, created_date, created_by, scheme_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE scheme_name=VALUES(scheme_name)
            """,
            sm
        )
    print(f"  [+] Seeded {len(share_masters)} rows into tbl_share_account_master")

    # 7. Seed tbl_share_account
    share_accounts = [
        (1, 1, 1, "SH0001", "2026-09-01", 1, "ACTIVE", 100),
        (2, 1, 2, "SH0002", "2026-09-02", 1, "ACTIVE", 150),
        (3, 1, 3, "SH0003", "2026-09-03", 1, "ACTIVE", 200),
        (4, 1, 4, "SH0004", "2026-09-04", 1, "ACTIVE", 75),
    ]
    for sa in share_accounts:
        cursor.execute(
            """
            INSERT INTO tbl_share_account
            (share_id, branch_id, cust_id, share_acc_no, acc_open_date, scheme_id, share_status, share_qty)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE share_qty=VALUES(share_qty)
            """,
            sa
        )
    print(f"  [+] Seeded {len(share_accounts)} rows into tbl_share_account")

    # 8. Seed tbl_sb_account (Savings Bank)
    sb_accounts = [
        (1, 1, "SB0001", "Self", "2026-09-01", 3.50, "ACTIVE", 1, 1, 45200.50),
        (2, 1, "SB0002", "Self", "2026-09-02", 3.50, "ACTIVE", 1, 1, 12850.00),
        (3, 1, "SB0003", "Self", "2026-09-03", 3.50, "ACTIVE", 1, 1, 89400.00),
        (4, 1, "SB0004", "Self", "2026-09-04", 3.50, "ACTIVE", 1, 1, 23150.75),
        (5, 1, "SB0005", "Self", "2026-09-04", 3.50, "ACTIVE", 1, 1, 67200.00),
        (6, 1, "SB0006", "Self", "2026-09-05", 3.50, "ACTIVE", 1, 1, 15400.20),
        (7, 1, "SB0007", "Self", "2026-09-06", 3.50, "ACTIVE", 1, 1, 98100.00),
    ]
    for sba in sb_accounts:
        cursor.execute(
            """
            INSERT INTO tbl_sb_account
            (sb_id, branch_id, sb_acc_no, acc_relationship, sb_opening_date, sb_intrest_rate, sb_status, is_active, scheme_id, sb_balance)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE sb_balance=VALUES(sb_balance)
            """,
            sba
        )
    print(f"  [+] Seeded {len(sb_accounts)} rows into tbl_sb_account")

    # 9. Seed tbl_fd_transaction
    fd_transactions = [
        (1, 1, 1, 25000.0, 25000.0, 0.0, "2026-09-02", "2026-09-02 10:30:00", 1, "CREDIT"),
        (2, 1, 2, 50000.0, 50000.0, 0.0, "2026-09-03", "2026-09-03 11:15:00", 1, "CREDIT"),
        (3, 1, 3, 100000.0, 100000.0, 0.0, "2026-09-03", "2026-09-03 14:00:00", 1, "CREDIT"),
        (4, 1, 4, 75000.0, 75000.0, 0.0, "2026-09-04", "2026-09-04 15:45:00", 1, "CREDIT"),
        (5, 1, 5, 30000.0, 30000.0, 0.0, "2026-09-05", "2026-09-05 09:20:00", 1, "CREDIT"),
    ]
    for fdt in fd_transactions:
        cursor.execute(
            """
            INSERT INTO tbl_fd_transaction
            (fd_trans_id, branch_id, fd_acc_id, fd_trans_amt, credit_amt, debit_amt, fd_trans_date, fd_trans_on, fd_trans_by, fd_trans_type)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE fd_trans_amt=VALUES(fd_trans_amt)
            """,
            fdt
        )
    print(f"  [+] Seeded {len(fd_transactions)} rows into tbl_fd_transaction")

    cursor.execute("SET FOREIGN_KEY_CHECKS = 1")
    conn.close()
    print("[SUCCESS] Demo data seeding for esahakara_demo completed successfully.")


if __name__ == "__main__":
    seed_demo_data()
