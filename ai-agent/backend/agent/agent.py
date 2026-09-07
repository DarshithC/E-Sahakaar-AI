# backend/agent/agent.py

import re
from datetime import datetime

from rag import (
    normalize,
    extract_customer_id,
    detect_date_period,
    retrieve_intent,
    is_details_followup,
    explicitly_all_customers,
)

from conversation import (
    get_session,
    update_session,
    add_message,
    get_last_customer_ids,
)

from .database_agent import (
    get_customer,
    get_customer_count,
    get_customers_by_period,
    get_customer_name,
    get_transactions,
    get_transaction_count,
    get_transaction_total,
    get_product_records,
    get_fd_schemes,
    get_rd_schemes,
    get_share_schemes,
)

from .response import (
    customer_details,
    transaction_response,
    amount_response,
    product_response,
    fd_schemes_response,
    rd_schemes_response,
    all_schemes_response,
)

from ai_model.response_engine import (
    generate_response,
)

from ai_model.cbs_validator import (
    validate_customer_full,
    validate_all_customers,
    quick_validate_customer,
)

from ai_model.anomaly_detector import (
    get_detector,
)


# ============================================================
# LOCAL SMALL TALK
# ============================================================

def instant_chat(text):

    t = normalize(text)

    greetings = [
        "hi",
        "hello",
        "hey",
        "hii",
        "hiii",
        "hello there",
        "hey there",
    ]

    if t in greetings:

        hour = datetime.now().hour

        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        return (
            f"{greeting}! 👋\n\n"
            "Welcome to E-Sahakara AI Assistant.\n\n"
            "I can help you with customer information, "
            "transactions, FD, RD, share accounts, "
            "onboarding, dates, times and document validation.\n\n"
            "How can I help you today?"
        )

    if t in [
        "how are you",
        "how are you doing",
        "how r you",
        "how r u",
        "are you okay",
        "are you fine",
    ]:

        return (
            "I'm doing well, thank you! 😊\n\n"
            "I'm ready to help with customer information, "
            "transactions, accounts, dates and validation."
        )

    if t in [
        "thanks",
        "thank you",
        "thankyou",
        "thanks a lot",
    ]:

        return (
            "You're welcome! 😊 "
            "I'm happy to help."
        )

    if t in [
        "bye",
        "goodbye",
        "see you",
        "see you later",
    ]:

        return (
            "Goodbye! 👋 "
            "Feel free to come back whenever you need help."
        )

    if t in [
        "help",
        "what can you do",
        "i need help",
        "can you help me",
    ]:

        return (
            "Of course! 😊\n\n"
            "I can help with:\n"
            "• Customer details\n"
            "• Customer count\n"
            "• Customer onboarding and creation time\n"
            "• Transaction history\n"
            "• Transaction counts and amounts\n"
            "• FD, RD and share accounts\n"
            "• PAN/Aadhaar validation\n"
            "• Today, yesterday, this week, this month and this year"
        )

    return None


# ============================================================
# CUSTOMER CREATION
# ============================================================

def handle_customer_creation(
    message,
    session_id,
    customer_id,
    period,
):

    # --------------------------------------------------------
    # Specific customer creation date
    # --------------------------------------------------------

    if customer_id is not None:

        customer = get_customer(
            customer_id
        )

        if not customer:

            return (
                f"I couldn't find customer "
                f"{customer_id} in the database."
            )

        created = (
            customer.get("created_at")
            or customer.get("created_on")
            or customer.get("created_date")
            or customer.get("onboarded_at")
            or customer.get("onboarding_date")
        )

        from .database_agent import (
            format_datetime
        )

        answer = (
            f"Customer {customer_id} "
            f"was created/onboarded on "
            f"{format_datetime(created)}."
        )

        update_session(
            session_id,
            last_intent="CUSTOMER_CREATION",
            last_customer_id=customer_id,
            last_period=period,
        )

        return answer

    # --------------------------------------------------------
    # Period based creation
    # --------------------------------------------------------

    period = period or "today"

    rows, date_column = (
        get_customers_by_period(
            period
        )
    )

    ids = []

    for row in rows:

        customer_id_value = row.get(
            "customer_id"
        )

        if customer_id_value is not None:

            ids.append(
                int(customer_id_value)
            )

    update_session(
        session_id,
        last_intent="CUSTOMER_CREATION",
        last_period=period,
        last_customer_ids=ids,
        last_customer_id=None,
    )

    if not rows:

        return (
            f"No customers were created "
            f"{period}."
        )

    return (
        f"{len(rows)} customer"
        f"{'s' if len(rows) != 1 else ''} "
        f"were created {period}."
    )


# ============================================================
# CUSTOMER DETAILS
# ============================================================

def handle_customer_details(
    message,
    session_id,
    customer_id,
):

    session = get_session(
        session_id
    )

    # Explicit customer ID has priority.
    if customer_id is not None:

        customer = get_customer(
            customer_id
        )

        update_session(
            session_id,
            last_intent="CUSTOMER_DETAILS",
            last_customer_id=customer_id,
            last_customer_ids=[
                customer_id
            ],
        )

        if not customer:

            return (
                f"I couldn't find customer "
                f"{customer_id} in the database."
            )

        return (
            f"Here are the details "
            f"of customer {customer_id}:\n\n"
            + customer_details(customer)
        )

    # --------------------------------------------------------
    # Previous customer list
    # --------------------------------------------------------

    previous_ids = session.get(
        "last_customer_ids",
        []
    )

    if previous_ids:

        answers = []

        for cid in previous_ids:

            customer = get_customer(cid)

            if customer:

                answers.append(
                    f"Customer {cid}\n\n"
                    + customer_details(
                        customer
                    )
                )

        if answers:

            update_session(
                session_id,
                last_intent="CUSTOMER_DETAILS",
            )

            return (
                "Here are the details "
                "of the customers:\n\n"
                + "\n\n"
                + ("-" * 35)
                + "\n\n"
                .join(answers)
            )

    # --------------------------------------------------------
    # Previous single customer
    # --------------------------------------------------------

    previous_customer = session.get(
        "last_customer_id"
    )

    if previous_customer is not None:

        customer = get_customer(
            previous_customer
        )

        if customer:

            return (
                f"Here are the details "
                f"of customer {previous_customer}:\n\n"
                + customer_details(
                    customer
                )
            )

    return (
        "Please provide a customer ID, "
        "for example: \"Show customer 3.\""
    )


# ============================================================
# TRANSACTIONS
# ============================================================

def handle_transactions(
    message,
    session_id,
    customer_id,
    period,
):

    text = normalize(message)

    session = get_session(
        session_id
    )

    # --------------------------------------------------------
    # IMPORTANT:
    # "overall", "all customers", etc. must NOT inherit
    # previous customer ID.
    # --------------------------------------------------------

    if explicitly_all_customers(message):

        actual_customer_id = None

    elif customer_id is not None:

        actual_customer_id = customer_id

    else:

        actual_customer_id = (
            session.get(
                "last_transaction_customer_id"
            )
            or session.get(
                "last_customer_id"
            )
        )

    # --------------------------------------------------------
    # Period
    # --------------------------------------------------------

    actual_period = (
        period
        if period is not None
        else session.get(
            "last_period"
        )
    )

    # --------------------------------------------------------
    # Query database
    # --------------------------------------------------------

    rows, date_column = get_transactions(
        customer_id=actual_customer_id,
        period=actual_period,
    )

    customer_name = None

    if actual_customer_id is not None:

        customer = get_customer(
            actual_customer_id
        )

        customer_name = get_customer_name(
            customer
        )

    # --------------------------------------------------------
    # COUNT
    # --------------------------------------------------------

    if (
        "how many" in text
        or "count" in text
        or "number of" in text
    ):

        count = len(rows)

        if actual_customer_id is not None:

            scope = (
                f"for customer "
                f"{actual_customer_id}"
            )

        else:

            scope = "for all customers"

        if actual_period:
            scope += f" {actual_period}"

        answer = (
            f"{count} transaction"
            f"{'s' if count != 1 else ''} "
            f"were recorded {scope}."
        )

    # --------------------------------------------------------
    # Otherwise transaction history
    # --------------------------------------------------------

    else:

        answer = transaction_response(
            rows,
            customer_name=customer_name,
            period=actual_period,
        )

    update_session(
        session_id,
        last_intent="TRANSACTIONS",
        last_customer_id=actual_customer_id,
        last_transaction_customer_id=actual_customer_id,
        last_period=actual_period,
        last_table="fd_transactions",
    )

    return answer


# ============================================================
# TRANSACTION AMOUNT
# ============================================================

def handle_transaction_amount(
    message,
    session_id,
    customer_id,
    period,
):

    session = get_session(
        session_id
    )

    if explicitly_all_customers(message):

        actual_customer_id = None

    elif customer_id is not None:

        actual_customer_id = customer_id

    else:

        actual_customer_id = (
            session.get(
                "last_transaction_customer_id"
            )
        )

    actual_period = (
        period
        if period is not None
        else session.get(
            "last_period"
        )
    )

    total, count = (
        get_transaction_total(
            customer_id=actual_customer_id,
            period=actual_period,
        )
    )

    customer_name = None

    if actual_customer_id is not None:

        customer = get_customer(
            actual_customer_id
        )

        customer_name = get_customer_name(
            customer
        )

    answer = amount_response(
        total,
        count,
        customer_name=customer_name,
        period=actual_period,
    )

    update_session(
        session_id,
        last_intent="TRANSACTION_AMOUNT",
        last_customer_id=actual_customer_id,
        last_transaction_customer_id=actual_customer_id,
        last_period=actual_period,
    )

    return answer


# ============================================================
# FD / RD / SHARE
# ============================================================

def handle_product(
    product,
    message,
    session_id,
    customer_id,
    period,
):

    table_map = {
        "FD": "fd",
        "RD": "rd",
        "SHARE": "share_account",
    }

    label_map = {
        "FD": "fixed deposit",
        "RD": "recurring deposit",
        "SHARE": "share-account",
    }

    table = table_map[product]

    label = label_map[product]

    session = get_session(
        session_id
    )

    actual_customer_id = (
        customer_id
        if customer_id is not None
        else session.get(
            "last_customer_id"
        )
    )

    actual_period = (
        period
        if period is not None
        else session.get(
            "last_period"
        )
    )

    rows, date_column = (
        get_product_records(
            table,
            customer_id=actual_customer_id,
            period=actual_period,
        )
    )

    update_session(
        session_id,
        last_intent=product,
        last_product=product,
        last_customer_id=actual_customer_id,
        last_period=actual_period,
        last_table=table,
    )

    if not rows:

        scope = ""

        if actual_customer_id is not None:
            scope += (
                f" for customer "
                f"{actual_customer_id}"
            )

        if actual_period:
            scope += (
                f" {actual_period}"
            )

        return (
            f"No {label} records were found"
            f"{scope}."
        )

    # Count
    text = normalize(message)

    if (
        "how many" in text
        or re.search(r"\bcount\b", text)
        or "number of" in text
    ):

        return (
            f"There {'is' if len(rows) == 1 else 'are'} "
            f"{len(rows)} {label} "
            f"record{'s' if len(rows) != 1 else ''}"
            f"{' for ' + actual_period if actual_period else ''}."
        )

    # Details
    cust_row = get_customer(actual_customer_id) if actual_customer_id else None
    cust_name = get_customer_name(cust_row) if cust_row else None
    return product_response(
        rows,
        product,
        period=actual_period,
        customer_name=cust_name,
    )


# ============================================================
# SCHEMES INTELLIGENCE
# ============================================================

def handle_fd_schemes(session_id):
    rows = get_fd_schemes()
    update_session(session_id, last_intent="FD_SCHEMES")
    return fd_schemes_response(rows)


def handle_rd_schemes(session_id):
    rows = get_rd_schemes()
    update_session(session_id, last_intent="RD_SCHEMES")
    return rd_schemes_response(rows)


def handle_all_schemes(session_id):
    fd_rows = get_fd_schemes()
    rd_rows = get_rd_schemes()
    share_rows = get_share_schemes()
    update_session(session_id, last_intent="ALL_SCHEMES")
    return all_schemes_response(fd_rows, rd_rows, share_rows)


# ============================================================
# VALIDATION
# ============================================================

def handle_validation(
    intent,
    message,
    session_id,
    customer_id,
):

    session = get_session(
        session_id
    )

    actual_customer_id = (
        customer_id
        if customer_id is not None
        else session.get(
            "last_customer_id"
        )
    )

    if actual_customer_id is None:

        return (
            "Please provide the customer ID "
            "whose document you want me to validate."
        )

    # Use the custom AI model for validation
    if intent == "PAN_VALIDATION":
        scope = "pan"
    elif intent == "AADHAAR_VALIDATION":
        scope = "aadhaar"
    else:
        scope = "all"

    answer = quick_validate_customer(
        actual_customer_id,
        scope=scope,
    )

    update_session(
        session_id,
        last_intent=intent,
        last_customer_id=actual_customer_id,
        last_validation=intent,
    )

    return answer


# ============================================================
# FULL CBS VALIDATION (NEW)
# ============================================================

def handle_full_cbs_validation(
    message,
    session_id,
    customer_id,
):
    """
    Run full CBS validation with confidence scoring
    and anomaly detection.
    """

    session = get_session(
        session_id
    )

    actual_customer_id = (
        customer_id
        if customer_id is not None
        else session.get(
            "last_customer_id"
        )
    )

    if actual_customer_id is None:

        return (
            "Please provide the customer ID "
            "for validation. For example: "
            "\"Validate customer 5\""
        )

    result = validate_customer_full(
        actual_customer_id
    )

    update_session(
        session_id,
        last_intent="FULL_CBS_VALIDATION",
        last_customer_id=actual_customer_id,
        last_validation="FULL_CBS_VALIDATION",
    )

    return result.get(
        "report",
        "Validation could not be completed."
    )


# ============================================================
# VALIDATE ALL CUSTOMERS (NEW)
# ============================================================

def handle_validate_all(
    message,
    session_id,
):
    """
    Run bulk validation on all customers.
    """

    result = validate_all_customers()

    update_session(
        session_id,
        last_intent="VALIDATE_ALL_CUSTOMERS",
        last_validation="VALIDATE_ALL_CUSTOMERS",
    )

    return result.get(
        "report",
        "Bulk validation could not be completed."
    )


# ============================================================
# RISK ASSESSMENT (NEW)
# ============================================================

def handle_risk_assessment(
    message,
    session_id,
    customer_id,
):
    """
    Run anomaly detection and risk assessment.
    """

    session = get_session(
        session_id
    )

    actual_customer_id = (
        customer_id
        if customer_id is not None
        else session.get(
            "last_customer_id"
        )
    )

    if actual_customer_id is None:

        return (
            "Please provide the customer ID "
            "for risk assessment. For example: "
            "\"Risk score for customer 5\""
        )

    # Get customer data
    customer = get_customer(
        actual_customer_id
    )

    if not customer:

        return (
            f"Customer {actual_customer_id} "
            "was not found in the database."
        )

    # Run anomaly detection
    detector = get_detector()

    anomaly_result = detector.score_customer(
        customer
    )

    name = get_customer_name(customer) or "Unknown"

    # Build response
    score = anomaly_result.get(
        "anomaly_score", 0
    )

    is_anomaly = anomaly_result.get(
        "is_anomaly", False
    )

    reasons = anomaly_result.get(
        "reasons", []
    )

    lines = [
        f"Risk Assessment for Customer "
        f"{actual_customer_id} ({name})",
        "━" * 35,
        "",
        f"Anomaly Score: {score:.3f}",
        f"Status: {'⚠️ FLAGGED' if is_anomaly else '✅ NORMAL'}",
    ]

    if reasons:
        lines.append("")
        lines.append("Findings:")

        for reason in reasons:
            lines.append(f"• {reason}")

    else:
        lines.append("")
        lines.append(
            "No anomalies detected in "
            "this customer's data."
        )

    update_session(
        session_id,
        last_intent="RISK_ASSESSMENT",
        last_customer_id=actual_customer_id,
    )

    return "\n".join(lines)


# ============================================================
# CONTEXT RESOLVER
# ============================================================

def resolve_context(
    message,
    session_id,
):

    session = get_session(
        session_id
    )

    result = retrieve_intent(
        message
    )

    intent = result["intent"]

    customer_id = result[
        "customer_id"
    ]

    period = result[
        "date_period"
    ]

    text = normalize(
        message
    )

    # --------------------------------------------------------
    # Customer ID from previous context
    # --------------------------------------------------------

    if customer_id is None:

        # Do not blindly inherit customer ID
        # for all-customer questions.
        if not (
            "all customers" in text
            or "all users" in text
            or "overall" in text
        ):

            customer_id = (
                session.get(
                    "last_customer_id"
                )
            )

    # --------------------------------------------------------
    # Date period
    # --------------------------------------------------------

    if period is None:

        period = session.get(
            "last_period"
        )

    # ========================================================
    # DETAILS FOLLOW-UP
    # ========================================================

    if is_details_followup(message):

        previous_intent = session.get(
            "last_intent"
        )

        previous_ids = session.get(
            "last_customer_ids",
            []
        )

        # If previous result was customer creation,
        # "give the details" means details of those
        # customers.
        if (
            previous_intent
            in [
                "CUSTOMER_CREATION",
                "CUSTOMER_DETAILS",
            ]
            and previous_ids
        ):

            intent = "CUSTOMER_DETAILS"

            customer_id = None

        # If previous question was transaction related,
        # "give the details" means transaction details.
        elif previous_intent in [
            "TRANSACTIONS",
            "TRANSACTION_COUNT",
            "TRANSACTION_AMOUNT",
        ]:

            intent = "TRANSACTIONS"

        elif previous_intent in [
            "FD",
            "RD",
            "SHARE",
        ]:

            intent = previous_intent

    # ========================================================
    # SHORT DATE FOLLOW-UP
    # ========================================================

    if (
        len(text.split()) <= 7
        and detect_date_period(text)
    ):

        if session.get(
            "last_intent"
        ) in [
            "TRANSACTIONS",
            "TRANSACTION_COUNT",
            "TRANSACTION_AMOUNT",
            "CUSTOMER_CREATION",
            "FD",
            "RD",
            "SHARE",
        ]:

            intent = session[
                "last_intent"
            ]

    # ========================================================
    # "CUSTOMER 3"
    # ========================================================

    if (
        customer_id is not None
        and len(text.split()) <= 5
        and (
            text.startswith("customer ")
            or text.startswith("user ")
            or text.startswith("member ")
        )
    ):

        previous_intent = session.get(
            "last_intent"
        )

        if previous_intent in [
            "TRANSACTIONS",
            "TRANSACTION_COUNT",
            "TRANSACTION_AMOUNT",
        ]:

            intent = previous_intent

        elif previous_intent in [
            "CUSTOMER_CREATION",
            "CUSTOMER_DETAILS",
        ]:

            intent = "CUSTOMER_DETAILS"

    # ========================================================
    # "IS IT VALID?"
    # ========================================================

    if text in [
        "is it valid",
        "is it valid",
        "is this valid",
        "is that valid",
        "valid",
        "is it correct",
        "is this correct",
    ]:

        previous_validation = (
            session.get(
                "last_validation"
            )
        )

        if previous_validation:

            intent = previous_validation

        else:

            # If previous customer query contained PAN,
            # use PAN validation.
            previous_history = session.get(
                "history",
                []
            )

            if previous_history:

                previous_user_messages = [
                    item["content"]
                    for item in previous_history
                    if item["role"] == "user"
                ]

                if previous_user_messages:

                    previous_text = normalize(
                        previous_user_messages[-1]
                    )

                    if "pan" in previous_text:

                        intent = "PAN_VALIDATION"

                    elif "aadhaar" in previous_text:

                        intent = "AADHAAR_VALIDATION"

    return {
        "intent": intent,
        "customer_id": customer_id,
        "period": period,
    }


# ============================================================
# MAIN AGENT
# ============================================================

async def process_message(
    message,
    session_id="default",
):

    message = (message or "").strip()

    if not message:

        return (
            "Please enter a question."
        )

    get_session(
        session_id
    )

    add_message(
        session_id,
        "user",
        message,
    )

    print(
        f"\n[E-SAHAKARA USER] {message}"
    )

    # --------------------------------------------------------
    # Instant local conversation
    # --------------------------------------------------------

    instant = instant_chat(
        message
    )

    if instant:

        add_message(
            session_id,
            "assistant",
            instant,
        )

        update_session(
            session_id,
            last_intent="GENERAL",
            last_answer=instant,
        )

        return instant

    # --------------------------------------------------------
    # Resolve intent
    # --------------------------------------------------------

    context = resolve_context(
        message,
        session_id,
    )

    intent = context[
        "intent"
    ]

    customer_id = context[
        "customer_id"
    ]

    period = context[
        "period"
    ]

    print(
        "[E-SAHAKARA INTENT]",
        intent,
        "CUSTOMER:",
        customer_id,
        "PERIOD:",
        period,
    )

    try:

        # ====================================================
        # CUSTOMER COUNT
        # ====================================================

        if intent == "CUSTOMER_COUNT":

            count = get_customer_count()

            answer = (
                f"There are currently "
                f"{count} customers in the "
                "banking database."
            )

        # ====================================================
        # CUSTOMER CREATION
        # ====================================================

        elif intent == "CUSTOMER_CREATION":

            answer = handle_customer_creation(
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # CUSTOMER DETAILS
        # ====================================================

        elif intent == "CUSTOMER_DETAILS":

            answer = handle_customer_details(
                message,
                session_id,
                customer_id,
            )

        # ====================================================
        # TRANSACTION COUNT
        # ====================================================

        elif intent == "TRANSACTION_COUNT":

            answer = handle_transactions(
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # TRANSACTION AMOUNT
        # ====================================================

        elif intent == "TRANSACTION_AMOUNT":

            answer = handle_transaction_amount(
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # TRANSACTIONS
        # ====================================================

        elif intent == "TRANSACTIONS":

            answer = handle_transactions(
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # FD
        # ====================================================

        elif intent == "FD":

            answer = handle_product(
                "FD",
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # RD
        # ====================================================

        elif intent == "RD":

            answer = handle_product(
                "RD",
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # SCHEMES INTELLIGENCE
        # ====================================================

        elif intent == "FD_SCHEMES":

            answer = handle_fd_schemes(session_id)

        elif intent == "RD_SCHEMES":

            answer = handle_rd_schemes(session_id)

        elif intent in ("ALL_SCHEMES", "SHARE_SCHEMES"):

            answer = handle_all_schemes(session_id)

        # ====================================================
        # SHARE
        # ====================================================

        elif intent == "SHARE":

            answer = handle_product(
                "SHARE",
                message,
                session_id,
                customer_id,
                period,
            )

        # ====================================================
        # VALIDATION
        # ====================================================

        elif intent in [
            "PAN_VALIDATION",
            "AADHAAR_VALIDATION",
            "IDENTITY_VALIDATION",
        ]:

            answer = handle_validation(
                intent,
                message,
                session_id,
                customer_id,
            )

        # ====================================================
        # FULL CBS VALIDATION (NEW)
        # ====================================================

        elif intent == "FULL_CBS_VALIDATION":

            answer = handle_full_cbs_validation(
                message,
                session_id,
                customer_id,
            )

        # ====================================================
        # VALIDATE ALL CUSTOMERS (NEW)
        # ====================================================

        elif intent == "VALIDATE_ALL_CUSTOMERS":

            answer = handle_validate_all(
                message,
                session_id,
            )

        # ====================================================
        # RISK ASSESSMENT (NEW)
        # ====================================================

        elif intent == "RISK_ASSESSMENT":

            answer = handle_risk_assessment(
                message,
                session_id,
                customer_id,
            )

        # ====================================================
        # GENERAL — Custom Response Engine (No Ollama)
        # ====================================================

        else:

            answer = generate_response(
                message,
                get_session(session_id),
            )

            update_session(
                session_id,
                last_intent="GENERAL",
            )

    except Exception as exc:

        print(
            "\n[E-SAHAKARA DATABASE/AGENT ERROR]"
        )

        print(
            repr(exc)
        )

        answer = (
            "I couldn't complete that database request. "
            "Please check the FastAPI terminal for the "
            "exact error."
        )

    add_message(
        session_id,
        "assistant",
        answer,
    )

    update_session(
        session_id,
        last_answer=answer,
    )

    return answer