"""
E-Sahakara AI Question Bank

The question bank is used as the retrieval knowledge base.
It is NOT used to fabricate database answers.

Actual banking answers always come from MySQL.
"""

QUESTION_BANK = [

    # ========================================================
    # GREETINGS
    # ========================================================

    {"question": "hi", "intent": "GREETING"},
    {"question": "hello", "intent": "GREETING"},
    {"question": "hey", "intent": "GREETING"},
    {"question": "hii", "intent": "GREETING"},
    {"question": "hiii", "intent": "GREETING"},
    {"question": "good morning", "intent": "GREETING"},
    {"question": "good afternoon", "intent": "GREETING"},
    {"question": "good evening", "intent": "GREETING"},
    {"question": "how are you", "intent": "GREETING"},
    {"question": "how are you doing", "intent": "GREETING"},

    # ========================================================
    # CUSTOMER COUNT
    # ========================================================

    {"question": "how many customers are there", "intent": "CUSTOMER_COUNT"},
    {"question": "how many users are there", "intent": "CUSTOMER_COUNT"},
    {"question": "how many members are there", "intent": "CUSTOMER_COUNT"},
    {"question": "what is the customer count", "intent": "CUSTOMER_COUNT"},
    {"question": "what is the total number of customers", "intent": "CUSTOMER_COUNT"},
    {"question": "give me total customers", "intent": "CUSTOMER_COUNT"},
    {"question": "how many account holders are there", "intent": "CUSTOMER_COUNT"},

    # ========================================================
    # CUSTOMER DETAILS
    # ========================================================

    {"question": "show customer 1", "intent": "CUSTOMER_DETAILS"},
    {"question": "give me details of customer 1", "intent": "CUSTOMER_DETAILS"},
    {"question": "customer information for customer 1", "intent": "CUSTOMER_DETAILS"},
    {"question": "show customer profile", "intent": "CUSTOMER_DETAILS"},
    {"question": "give me customer information", "intent": "CUSTOMER_DETAILS"},
    {"question": "show me user details", "intent": "CUSTOMER_DETAILS"},

    # ========================================================
    # ONBOARDING COUNT
    # ========================================================

    {"question": "how many customers were onboarded today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many customers were created today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many users joined today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many customers registered today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many new customers were added today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many accounts were created today", "intent": "ONBOARDING_COUNT"},
    {"question": "how many customers were onboarded yesterday", "intent": "ONBOARDING_COUNT"},

    # ========================================================
    # ONBOARDING DETAILS
    # ========================================================

    {"question": "which customers were onboarded today", "intent": "ONBOARDING_DETAILS"},
    {"question": "show customers created today", "intent": "ONBOARDING_DETAILS"},
    {"question": "give me details of customers onboarded today", "intent": "ONBOARDING_DETAILS"},
    {"question": "who joined the bank today", "intent": "ONBOARDING_DETAILS"},
    {"question": "who was registered today", "intent": "ONBOARDING_DETAILS"},
    {"question": "show today's new customers", "intent": "ONBOARDING_DETAILS"},
    {"question": "give me their details", "intent": "ONBOARDING_DETAILS"},

    # ========================================================
    # TRANSACTIONS
    # ========================================================

    {"question": "show transactions of customer 1", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "show transaction details of customer 2", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "give me transaction history of customer 3", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "show payments of customer 4", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "show transfers for customer 5", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "what transactions did customer 1 make", "intent": "CUSTOMER_TRANSACTIONS"},
    {"question": "show banking activity of customer 2", "intent": "CUSTOMER_TRANSACTIONS"},

    # ========================================================
    # TRANSACTIONS BY DATE
    # ========================================================

    {"question": "what transactions happened today", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "how many transactions happened today", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "transactions from today", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "what payments happened yesterday", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "show today's transfers", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "transactions on 2026-09-04", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},
    {"question": "what happened in transactions yesterday", "intent": "CUSTOMER_TRANSACTIONS_BY_DATE"},

    # ========================================================
    # FD
    # ========================================================

    {"question": "show fixed deposits", "intent": "FD_DETAILS"},
    {"question": "show fd accounts", "intent": "FD_DETAILS"},
    {"question": "give me fd details", "intent": "FD_DETAILS"},
    {"question": "which customers opened fixed deposits", "intent": "FD_DETAILS"},
    {"question": "show fixed deposit information", "intent": "FD_DETAILS"},
    {"question": "which fd accounts were opened today", "intent": "FD_BY_DATE"},

    # ========================================================
    # RD
    # ========================================================

    {"question": "show recurring deposits", "intent": "RD_DETAILS"},
    {"question": "show rd accounts", "intent": "RD_DETAILS"},
    {"question": "give me rd details", "intent": "RD_DETAILS"},
    {"question": "which customers have recurring deposits", "intent": "RD_DETAILS"},
    {"question": "show recurring deposit information", "intent": "RD_DETAILS"},
    {"question": "which rd accounts were opened today", "intent": "RD_BY_DATE"},

    # ========================================================
    # SHARE
    # ========================================================

    {"question": "show share accounts", "intent": "SHARE_DETAILS"},
    {"question": "give me share details", "intent": "SHARE_DETAILS"},
    {"question": "which customers have shares", "intent": "SHARE_DETAILS"},
    {"question": "show share deposits", "intent": "SHARE_DETAILS"},
    {"question": "which shares were created today", "intent": "SHARE_BY_DATE"},

    # ========================================================
    # VALIDATION
    # ========================================================

    {"question": "validate customer 1 pan and aadhaar", "intent": "VALIDATE_CUSTOMER"},
    {"question": "check pan and aadhaar", "intent": "VALIDATE_CUSTOMER"},
    {"question": "verify customer documents", "intent": "VALIDATE_CUSTOMER"},
    {"question": "is the pan valid", "intent": "VALIDATE_CUSTOMER"},
    {"question": "is the aadhaar valid", "intent": "VALIDATE_CUSTOMER"},
    {"question": "check customer 2 pan", "intent": "VALIDATE_CUSTOMER"},
    {"question": "check customer 2 aadhaar", "intent": "VALIDATE_CUSTOMER"},

    # ========================================================
    # FULL CBS VALIDATION (NEW)
    # ========================================================

    {"question": "validate customer 1", "intent": "FULL_CBS_VALIDATION"},
    {"question": "run full validation on customer 5", "intent": "FULL_CBS_VALIDATION"},
    {"question": "run cbs validation on customer 3", "intent": "FULL_CBS_VALIDATION"},
    {"question": "full check on customer 2", "intent": "FULL_CBS_VALIDATION"},
    {"question": "complete validation for customer 4", "intent": "FULL_CBS_VALIDATION"},
    {"question": "validate all fields of customer 1", "intent": "FULL_CBS_VALIDATION"},
    {"question": "detailed validation for customer 3", "intent": "FULL_CBS_VALIDATION"},
    {"question": "cbs check customer 5", "intent": "FULL_CBS_VALIDATION"},

    # ========================================================
    # VALIDATE ALL CUSTOMERS (NEW)
    # ========================================================

    {"question": "validate all customers", "intent": "VALIDATE_ALL_CUSTOMERS"},
    {"question": "validate all users", "intent": "VALIDATE_ALL_CUSTOMERS"},
    {"question": "run validation on all customers", "intent": "VALIDATE_ALL_CUSTOMERS"},
    {"question": "bulk validation", "intent": "VALIDATE_ALL_CUSTOMERS"},
    {"question": "check all customers", "intent": "VALIDATE_ALL_CUSTOMERS"},

    # ========================================================
    # RISK ASSESSMENT (NEW)
    # ========================================================

    {"question": "what is the risk score for customer 1", "intent": "RISK_ASSESSMENT"},
    {"question": "risk assessment for customer 3", "intent": "RISK_ASSESSMENT"},
    {"question": "is customer 5 suspicious", "intent": "RISK_ASSESSMENT"},
    {"question": "anomaly score of customer 2", "intent": "RISK_ASSESSMENT"},
    {"question": "check anomaly for customer 4", "intent": "RISK_ASSESSMENT"},
    {"question": "any anomalies in customer 1", "intent": "RISK_ASSESSMENT"},
    {"question": "risk level of customer 3", "intent": "RISK_ASSESSMENT"},

    # ========================================================
    # SCHEMES INTELLIGENCE
    # ========================================================

    {"question": "how many fd schemes are there", "intent": "FD_SCHEMES"},
    {"question": "how many fd schemes are there?", "intent": "FD_SCHEMES"},
    {"question": "what are the fd schemes", "intent": "FD_SCHEMES"},
    {"question": "types of fd in the db", "intent": "FD_SCHEMES"},
    {"question": "types of fd schemes", "intent": "FD_SCHEMES"},
    {"question": "show all fd schemes", "intent": "FD_SCHEMES"},
    {"question": "list fd schemes", "intent": "FD_SCHEMES"},
    {"question": "what are the types of fd", "intent": "FD_SCHEMES"},
    {"question": "how many rd schemes are there", "intent": "RD_SCHEMES"},
    {"question": "what are the rd schemes", "intent": "RD_SCHEMES"},
    {"question": "types of rd schemes", "intent": "RD_SCHEMES"},
    {"question": "what schemes are available in the bank", "intent": "ALL_SCHEMES"},
    {"question": "how many schemes are there", "intent": "ALL_SCHEMES"},
    {"question": "show all schemes", "intent": "ALL_SCHEMES"},
]