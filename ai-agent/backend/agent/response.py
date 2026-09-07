# backend/agent/response.py

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional

from .database_agent import (
    format_datetime,
    get_customer_name,
    get_customer,
)


# ============================================================
# FRIENDLY FIELD DICTIONARY
# Maps raw DB column names to natural, conversational banking terms
# ============================================================

FRIENDLY_LABELS = {
    # Customer / Member Info
    "customer_id": "Member ID",
    "first_name": "First Name",
    "last_name": "Surname / Last Name",
    "relation_name": "Father / Guardian Name (C/o)",
    "phone_no": "Registered Mobile Number",
    "gender": "Gender",
    "residential_address": "Residential Address",
    "res_address": "Residential Address",
    "caste": "Social Category",
    "aadhaar_no": "Aadhaar Card (UIDAI)",
    "pan_no": "PAN Card Number",
    "status": "Membership / Account Status",
    "created_at": "Member Registration Date",
    "created_on": "Member Registration Date",
    "created_date": "Member Registration Date",
    "onboarded_at": "Member Registration Date",

    # Fixed Deposit (FD)
    "account_no": "Deposit Account Number",
    "scheme_name": "Deposit Scheme Name",
    "account_open_date": "Deposit Opening Date",
    "fd_amount": "Principal Deposit Amount",
    "maturity_date": "Maturity Date",
    "maturity_amount": "Expected Maturity Payout",
    "interest_rate": "Interest Rate (% p.a.)",

    # Recurring Deposit (RD)
    "rd_account_no": "Recurring Deposit Account Number",
    "principal_amount": "Monthly Installment Amount",
    "tenure": "Deposit Tenure (Duration)",

    # Share Account
    "total_shares": "Total Shares Held",
    "share_amount": "Total Share Capital Amount",
    "account_closed_date": "Share Closure Date",

    # Transactions
    "transaction_id": "Transaction Reference ID",
    "transaction_date": "Transaction Date & Time",
    "customer_name": "Customer Name",
    "description": "Transaction Remarks / Narration",
    "transaction_amount": "Transaction Amount",
    "transaction_type": "Transaction Type",
    "mode_of_pay": "Payment Channel / Mode",
}


def format_currency(value: Any) -> str:
    """Format numeric value as Rs. with commas."""
    if value is None:
        return "Rs. 0.00"
    try:
        dec = Decimal(str(value))
        return f"Rs. {dec:,.2f}"
    except Exception:
        return f"Rs. {value}"


# ============================================================
# CUSTOMER DETAILS
# ============================================================

def customer_details(customer: Dict[str, Any]) -> str:
    """Format customer record using friendly banking language."""

    if not customer:
        return "I couldn't find that customer in the database."

    customer_id = customer.get("customer_id", "Not available")
    name = get_customer_name(customer) or "Not available"
    relation = customer.get("relation_name", "Not available")
    phone = customer.get("phone_no", "Not available")
    gender = customer.get("gender", "Not available")
    address = (
        customer.get("residential_address")
        or customer.get("res_address")
        or "Not available"
    )
    caste = customer.get("caste", "Not available")
    aadhaar = customer.get("aadhaar_no", "Not available")
    pan = customer.get("pan_no", "Not available")
    status = customer.get("status", "Not available")
    created = (
        customer.get("created_at")
        or customer.get("created_on")
        or customer.get("created_date")
        or customer.get("onboarded_at")
        or customer.get("onboarding_date")
    )

    lines = [
        f"Member Profile — {name}",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        f"• Member ID: {customer_id}",
        f"• Account Holder Name: {name}",
        f"• Father / Guardian Name (C/o): {relation}",
        f"• Registered Mobile Number: {phone}",
        f"• Gender: {gender}",
        f"• Residential Address: {address}",
        f"• Social Category: {caste}",
        f"• PAN Card Number: {pan}",
        f"• Aadhaar Number (UIDAI): {aadhaar}",
        f"• Membership Status: {status}",
        f"• Member Registration Date: {format_datetime(created)}",
    ]

    return "\n".join(lines)


# ============================================================
# TRANSACTION RESPONSE
# ============================================================

def transaction_response(
    rows: List[Dict[str, Any]],
    customer_name: Optional[str] = None,
    period: Optional[str] = None,
) -> str:
    """Format transaction records in natural, friendly banking terms."""

    if customer_name:
        heading = f"Transaction Statement for {customer_name}"
    else:
        heading = "Recent Transaction Records"

    if period:
        heading += f" ({period.replace('_', ' ')})"

    if not rows:
        return (
            f"No transactions were found"
            f"{' for ' + customer_name if customer_name else ''}"
            f"{' for ' + period.replace('_', ' ') if period else ''}."
        )

    lines = [
        heading,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    from .database_agent import (
        find_column,
        DATE_COLUMNS,
        AMOUNT_COLUMNS,
        TRANSACTION_TYPE_COLUMNS,
        PAYMENT_MODE_COLUMNS,
        DESCRIPTION_COLUMNS,
        ACCOUNT_COLUMNS,
    )

    total_amount = Decimal("0.00")

    for idx, row in enumerate(rows, start=1):
        keys = list(row.keys())

        date_col = find_column(keys, DATE_COLUMNS)
        amount_col = find_column(keys, AMOUNT_COLUMNS)
        type_col = find_column(keys, TRANSACTION_TYPE_COLUMNS)
        mode_col = find_column(keys, PAYMENT_MODE_COLUMNS)
        desc_col = find_column(keys, DESCRIPTION_COLUMNS)
        acc_col = find_column(keys, ACCOUNT_COLUMNS)

        date_val = format_datetime(row.get(date_col)) if date_col else "Date unavailable"
        acc_val = row.get(acc_col) if acc_col else None
        amt_val = row.get(amount_col)
        type_val = row.get(type_col)
        mode_val = row.get(mode_col)
        desc_val = row.get(desc_col)

        if amt_val is not None:
            try:
                total_amount += Decimal(str(amt_val))
            except Exception:
                pass

        card = [f"#{idx} | Date: {date_val}"]
        if acc_val:
            card.append(f"   Account Number: {acc_val}")
        if amt_val is not None:
            card.append(f"   Amount Transacted: {format_currency(amt_val)}")
        if type_val:
            type_label = "Deposit (Credit)" if str(type_val).upper() in ("DEPOSIT", "CREDIT") else (
                "Withdrawal (Debit)" if str(type_val).upper() in ("WITHDRAWAL", "DEBIT") else str(type_val)
            )
            card.append(f"   Transaction Type: {type_label}")
        if mode_val:
            card.append(f"   Payment Channel / Mode: {mode_val}")
        if desc_val:
            card.append(f"   Remarks / Narration: {desc_val}")

        lines.append("\n".join(card))
        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append(f"Summary: {len(rows)} transaction(s) | Total Volume: {format_currency(total_amount)}")

    return "\n".join(lines)


# ============================================================
# AMOUNT SUMMARY RESPONSE
# ============================================================

def amount_response(
    total: Any,
    count: int,
    customer_name: Optional[str] = None,
    period: Optional[str] = None,
) -> str:
    """Format total amount inquiry with friendly spoken language."""

    total_dec = Decimal(str(total or 0))

    scope = (
        f"for {customer_name}"
        if customer_name
        else "across all accounts"
    )

    if period:
        scope += f" for {period.replace('_', ' ')}"

    return (
        f"Total Transaction Summary:\n"
        f"• Cumulative Amount Transacted: {format_currency(total_dec)} ({scope})\n"
        f"• Total Transactions Recorded: {count} transaction(s)"
    )


# ============================================================
# PRODUCT RESPONSE (FD / RD / SHARE ACCOUNTS)
# ============================================================

def product_response(
    rows: List[Dict[str, Any]],
    product: str,
    period: Optional[str] = None,
    customer_name: Optional[str] = None,
) -> str:
    """Format banking product accounts (FD, RD, Share) with customized, human-friendly terms."""

    prod_upper = (product or "").upper()

    titles = {
        "FD": "Fixed Deposit (FD) Accounts",
        "RD": "Recurring Deposit (RD) Accounts",
        "SHARE": "Member Share Capital Accounts",
    }

    title = titles.get(prod_upper, f"{prod_upper} Accounts")

    if customer_name:
        title += f" for {customer_name}"
    if period:
        title += f" ({period.replace('_', ' ')})"

    if not rows:
        return f"No active {title.lower()} were found."

    lines = [
        title,
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    for idx, row in enumerate(rows, start=1):
        lines.append(f"Account Record #{idx}:")

        if prod_upper == "FD":
            acc_no = row.get("fd_acc_no") or row.get("account_no", "N/A")
            scheme = row.get("fd_scheme_name") or row.get("scheme_name", "Fixed Deposit")
            open_date = format_datetime(row.get("acc_open_date") or row.get("account_open_date"))
            fd_amt = format_currency(row.get("principal_amt") if row.get("principal_amt") is not None else row.get("fd_amount"))
            mat_date = format_datetime(row.get("maturity_date"))
            mat_amt = format_currency(row.get("maturity_amount"))
            status = row.get("status", "ACTIVE")
            cust_id = row.get("cust_id") or row.get("customer_id")
            cust_name = None
            if cust_id:
                try:
                    c_row = get_customer(cust_id)
                    if c_row:
                        cust_name = get_customer_name(c_row)
                except Exception:
                    pass

            lines.append(f"  • Deposit Account Number: {acc_no}")
            if customer_name:
                lines.append(f"  • Account Holder: {customer_name}")
            elif cust_name:
                lines.append(f"  • Account Holder: {cust_name} (Member ID: {cust_id})")
            elif cust_id:
                lines.append(f"  • Member ID: {cust_id}")
            lines.append(f"  • Deposit Scheme / Product: {scheme}")
            lines.append(f"  • Principal Deposit Amount: {fd_amt}")
            lines.append(f"  • Deposit Opening Date: {open_date}")
            if mat_date != "Date unavailable":
                lines.append(f"  • Maturity Date: {mat_date}")
            if mat_amt != "Rs. 0.00":
                lines.append(f"  • Expected Maturity Payout: {mat_amt}")
            lines.append(f"  • Deposit Status: {status}")

        elif prod_upper == "RD":
            rd_no = row.get("rd_acc_no") or row.get("rd_account_no", "N/A")
            open_date = format_datetime(row.get("acc_open_date") or row.get("account_open_date"))
            principal = format_currency(row.get("balance") if row.get("balance") is not None else row.get("principal_amount"))
            tenure = row.get("tenure", "12")
            mat_date = format_datetime(row.get("maturity_date"))
            mat_amt = format_currency(row.get("maturity_amount"))
            status = row.get("rd_status") or row.get("status", "ACTIVE")
            cust_id = row.get("cust_id") or row.get("customer_id")
            cust_name = None
            if cust_id:
                try:
                    c_row = get_customer(cust_id)
                    if c_row:
                        cust_name = get_customer_name(c_row)
                except Exception:
                    pass

            lines.append(f"  • Recurring Deposit Account Number: {rd_no}")
            if customer_name:
                lines.append(f"  • Account Holder: {customer_name}")
            elif cust_name:
                lines.append(f"  • Account Holder: {cust_name} (Member ID: {cust_id})")
            elif cust_id:
                lines.append(f"  • Member ID: {cust_id}")
            lines.append(f"  • Monthly Installment Amount: {principal}")
            lines.append(f"  • Deposit Tenure (Duration): {tenure} Months")
            lines.append(f"  • Account Opening Date: {open_date}")
            if mat_date != "Date unavailable":
                lines.append(f"  • Maturity Date: {mat_date}")
            if mat_amt != "Rs. 0.00":
                lines.append(f"  • Expected Maturity Value: {mat_amt}")
            lines.append(f"  • Account Status: {status}")

        elif prod_upper in ("SHARE", "SHARE_ACCOUNT"):
            acc_no = row.get("share_acc_no") or row.get("account_no", "N/A")
            member_id = row.get("cust_id") or row.get("customer_id", "N/A")
            shares = row.get("share_qty") or row.get("total_shares", 0)
            share_val = format_currency(row.get("share_amount") if row.get("share_amount") is not None else (Decimal(str(shares or 0)) * 100))
            open_date = format_datetime(row.get("acc_open_date") or row.get("account_open_date"))
            status = row.get("share_status") or row.get("status", "ACTIVE")
            cust_name = None
            if member_id and str(member_id).isdigit():
                try:
                    c_row = get_customer(int(member_id))
                    if c_row:
                        cust_name = get_customer_name(c_row)
                except Exception:
                    pass

            lines.append(f"  • Share Certificate / Account Number: {acc_no}")
            if customer_name:
                lines.append(f"  • Shareholder: {customer_name}")
            elif cust_name:
                lines.append(f"  • Shareholder: {cust_name} (Member ID: {member_id})")
            elif member_id:
                lines.append(f"  • Member ID: {member_id}")
            lines.append(f"  • Total Shares Held: {shares} Shares")
            lines.append(f"  • Total Share Capital Contribution: {share_val}")
            lines.append(f"  • Share Allotment Date: {open_date}")
            lines.append(f"  • Share Account Status: {status}")

        else:
            # Generic fallback with friendly label translation
            for col_name, val in row.items():
                label = FRIENDLY_LABELS.get(str(col_name).lower(), str(col_name).replace("_", " ").title())
                if "amount" in str(col_name).lower():
                    val_str = format_currency(val)
                elif "date" in str(col_name).lower() or "at" in str(col_name).lower():
                    val_str = format_datetime(val)
                else:
                    val_str = str(val if val is not None else "N/A")
                lines.append(f"  • {label}: {val_str}")

        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append(f"Total Accounts Found: {len(rows)}")

    return "\n".join(lines)


# ============================================================
# SCHEMES INTELLIGENCE RESPONSES
# ============================================================

def fd_schemes_response(rows: List[Dict[str, Any]]) -> str:
    """Format FD schemes and types available in the CBS database."""
    if not rows:
        return "There are currently no Fixed Deposit (FD) schemes recorded in the CBS database."

    total_schemes = len(rows)
    total_accounts = sum(r.get("account_count", 0) for r in rows)
    total_volume = sum(Decimal(str(r.get("total_deposit_volume", 0))) for r in rows)

    lines = [
        f"There are currently {total_schemes} types of Fixed Deposit (FD) schemes available in the CBS database:\n"
    ]

    for idx, r in enumerate(rows, 1):
        scheme_name = r.get("scheme_name", "Unknown Scheme")
        count = r.get("account_count", 0)
        min_dep = Decimal(str(r.get("min_deposit", 0)))
        max_dep = Decimal(str(r.get("max_deposit", 0)))
        vol = Decimal(str(r.get("total_deposit_volume", 0)))

        lines.append(f"{idx}. {scheme_name}")
        if min_dep == max_dep:
            lines.append(f"   • Deposit Amount: {format_currency(min_dep)}")
        else:
            lines.append(f"   • Deposit Range: {format_currency(min_dep)} to {format_currency(max_dep)}")
        lines.append(f"   • Active Member Accounts: {count}")
        lines.append(f"   • Total Deposited in Scheme: {format_currency(vol)}")
        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append(
        f"Summary: The CBS platform offers {total_schemes} distinct FD schemes with {total_accounts} active deposit accounts totaling {format_currency(total_volume)}."
    )
    return "\n".join(lines)


def rd_schemes_response(rows: List[Dict[str, Any]]) -> str:
    """Format RD tenure schemes available in the CBS database."""
    if not rows:
        return "There are currently no Recurring Deposit (RD) schemes recorded in the CBS database."

    total_schemes = len(rows)
    total_accounts = sum(r.get("account_count", 0) for r in rows)
    total_monthly = sum(Decimal(str(r.get("total_monthly_inflow", 0))) for r in rows)

    lines = [
        f"There are currently {total_schemes} Recurring Deposit (RD) tenure schemes available in the CBS database:\n"
    ]

    for idx, r in enumerate(rows, 1):
        tenure = r.get("tenure", 0)
        count = r.get("account_count", 0)
        min_inst = Decimal(str(r.get("min_installment", 0)))
        max_inst = Decimal(str(r.get("max_installment", 0)))
        min_mat = Decimal(str(r.get("min_maturity", 0)))
        max_mat = Decimal(str(r.get("max_maturity", 0)))

        try:
            tenure_num = int(re.search(r'\d+', str(tenure)).group(0))
        except Exception:
            tenure_num = 12
        years = max(1, tenure_num // 12)
        years_label = f"{years} Year" if years == 1 else f"{years} Years"
        lines.append(f"{idx}. {tenure_num}-Month Recurring Deposit ({years_label} Tenure)")
        if min_inst == max_inst:
            lines.append(f"   • Monthly Installment: {format_currency(min_inst)} / month")
        else:
            lines.append(f"   • Monthly Installment Range: {format_currency(min_inst)} to {format_currency(max_inst)} / month")
        lines.append(f"   • Expected Maturity Payout: {format_currency(min_mat)} to {format_currency(max_mat)}")
        lines.append(f"   • Active Member Accounts: {count}")
        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append(
        f"Summary: There are {total_schemes} RD tenure schemes serving {total_accounts} active member accounts, generating {format_currency(total_monthly)} in monthly recurring savings."
    )
    return "\n".join(lines)


def all_schemes_response(fd_rows: List[Dict[str, Any]], rd_rows: List[Dict[str, Any]], share_rows: List[Dict[str, Any]]) -> str:
    """Format a comprehensive overview of all CBS banking schemes and deposit options."""
    fd_count = len(fd_rows)
    rd_count = len(rd_rows)
    total_schemes = fd_count + rd_count + (1 if share_rows else 0)

    lines = [
        f"The E-Sahakara CBS platform currently offers {total_schemes} distinct deposit and membership schemes:\n"
    ]

    if fd_rows:
        lines.append(f"Fixed Deposit (FD) Schemes ({fd_count} Types):")
        for idx, r in enumerate(fd_rows, 1):
            name = r.get("scheme_name", "Unknown Scheme")
            cnt = r.get("account_count", 0)
            min_dep = Decimal(str(r.get("min_deposit", 0)))
            max_dep = Decimal(str(r.get("max_deposit", 0)))
            rng = format_currency(min_dep) if min_dep == max_dep else f"{format_currency(min_dep)} – {format_currency(max_dep)}"
            lines.append(f"  {idx}. {name} — {cnt} account(s) ({rng})")
        lines.append("")

    if rd_rows:
        lines.append(f"Recurring Deposit (RD) Schemes ({rd_count} Tenures):")
        for idx, r in enumerate(rd_rows, 1):
            tenure = r.get("tenure", 0)
            try:
                tenure_num = int(re.search(r'\d+', str(tenure)).group(0))
            except Exception:
                tenure_num = 12
            cnt = r.get("account_count", 0)
            min_inst = Decimal(str(r.get("min_installment", 0)))
            max_inst = Decimal(str(r.get("max_installment", 0)))
            rng = format_currency(min_inst) if min_inst == max_inst else f"{format_currency(min_inst)} – {format_currency(max_inst)}"
            lines.append(f"  {idx}. {tenure_num}-Month RD Plan ({max(1, tenure_num // 12)} Year) — {cnt} account(s) ({rng} / month)")
        lines.append("")

    if share_rows and share_rows[0].get("account_count"):
        sh = share_rows[0]
        cnt = sh.get("account_count", 0)
        tot_shares = sh.get("total_shares", 0)
        cap = format_currency(sh.get("total_share_capital", 0))
        lines.append("Cooperative Member Share Capital:")
        lines.append(f"  • Regular Member Shares — {cnt} member shareholders with {tot_shares} total shares ({cap} paid-up capital)")
        lines.append("")

    lines.append("────────────────────────────────────────")
    lines.append("To explore any scheme in detail, ask: \"Show FD schemes\" or \"Show RD schemes\".")
    return "\n".join(lines)