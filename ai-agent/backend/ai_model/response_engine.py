# ai_model/response_engine.py

"""
Smart Response Generator — Replaces Ollama.

Handles ALL conversation scenarios using template-based
Natural Language Generation (NLG) with context-awareness.

Responds in <1ms. Zero timeouts. Zero GPU. Zero external AI.
"""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional


# ============================================================
# TIME-AWARE GREETING
# ============================================================

def _get_greeting() -> str:
    """Time-of-day greeting."""

    hour = datetime.now().hour

    if hour < 12:
        return "Good morning"

    elif hour < 17:
        return "Good afternoon"

    else:
        return "Good evening"


# ============================================================
# GREETING RESPONSES
# ============================================================

GREETING_PATTERNS = {

    # Exact matches (normalized)
    "hi", "hii", "hiii", "hello", "hey",
    "heyy", "heyyy", "hello there",
    "hey there", "hi there",
}

GREETING_WITH_TIME = {
    "good morning", "good afternoon",
    "good evening",
}

HOW_ARE_YOU = {
    "how are you", "how are you doing",
    "how r u", "how r you",
    "how are u", "are you okay",
    "are you fine", "are you doing well",
}

THANKS = {
    "thanks", "thank you", "thankyou",
    "thank u", "thanks a lot",
    "many thanks", "thx",
}

GOODBYE = {
    "bye", "goodbye", "see you",
    "see you later", "see ya",
    "take care", "good night",
    "bye bye",
}

IDENTITY = {
    "who are you", "what are you",
    "tell me about yourself",
    "what is your name",
    "who built you",
    "what can you do",
    "what are your capabilities",
}

HELP = {
    "help", "i need help",
    "can you help me",
    "show me help",
    "how to use",
}


# ============================================================
# MAIN RESPONSE GENERATOR
# ============================================================

def generate_response(
    message: str,
    session: Dict[str, Any] = None,
) -> str:
    """
    Generate a response for any user message.

    This replaces Ollama for ALL conversation scenarios.
    It handles greetings, help, identity questions,
    unknown queries, and validation result formatting.

    Returns the response string.
    """

    if not message:
        return "How can I help you today?"

    text = (message or "").strip().lower()

    # Remove trailing punctuation for matching
    clean = re.sub(
        r"[!?.,;:]+$", "", text
    ).strip()

    # ========================================================
    # GREETINGS
    # ========================================================

    if clean in GREETING_PATTERNS:

        greeting = _get_greeting()

        return (
            f"{greeting}! 👋\n\n"
            "Welcome to E-Sahakara AI Assistant.\n\n"
            "I can help you with:\n"
            "• Customer details and information\n"
            "• Customer onboarding reports\n"
            "• Transaction history and amounts\n"
            "• FD, RD, and share accounts\n"
            "• PAN/Aadhaar/phone validation\n"
            "• Full CBS data validation with "
            "confidence scores\n"
            "• Anomaly detection\n\n"
            "How can I help you today?"
        )

    if clean in GREETING_WITH_TIME:

        return (
            f"{clean.title()}! 👋\n\n"
            "I'm E-Sahakara AI, your banking "
            "assistant. How can I help you today?"
        )

    # ========================================================
    # HOW ARE YOU
    # ========================================================

    if clean in HOW_ARE_YOU:

        return (
            "I'm doing great, thank you! 😊\n\n"
            "I'm ready to help with customer "
            "information, transactions, accounts, "
            "validation, and more."
        )

    # ========================================================
    # THANKS
    # ========================================================

    if clean in THANKS:

        return (
            "You're welcome! 😊 "
            "Let me know if you need anything else."
        )

    # ========================================================
    # GOODBYE
    # ========================================================

    if clean in GOODBYE:

        return (
            "Goodbye! 👋 "
            "Have a great day. Feel free to "
            "come back whenever you need help."
        )

    # ========================================================
    # IDENTITY
    # ========================================================

    if clean in IDENTITY:

        return (
            "I'm **E-Sahakara AI**, a custom-built "
            "banking assistant for the E-Sahakara "
            "cooperative banking system. 🏦\n\n"
            "I run entirely locally — no external "
            "AI services, no cloud calls. "
            "All data stays on your server.\n\n"
            "I can help with:\n"
            "• Customer details and lookup\n"
            "• Customer onboarding reports\n"
            "• Transaction history and summaries\n"
            "• FD, RD, and share account details\n"
            "• **Full CBS validation** with "
            "confidence scoring\n"
            "• PAN, Aadhaar, and phone validation\n"
            "• Anomaly detection on customer data\n"
            "• Duplicate PAN/Aadhaar/Phone detection"
        )

    # ========================================================
    # HELP
    # ========================================================

    if clean in HELP:

        return (
            "Of course! Here's what I can do: 😊\n\n"
            "**Customer Information:**\n"
            "• \"Show customer 5\" — get details\n"
            "• \"How many customers?\" — total count\n"
            "• \"Who was onboarded today?\" — creation\n\n"
            "**Transactions:**\n"
            "• \"Show transactions of customer 3\"\n"
            "• \"How many transactions today?\"\n"
            "• \"What is the total transaction amount?\"\n\n"
            "**Accounts:**\n"
            "• \"Show FD accounts\"\n"
            "• \"Show RD details\"\n"
            "• \"Show share accounts\"\n\n"
            "**Validation (New!):**\n"
            "• \"Validate customer 5\" — full CBS check\n"
            "• \"Check PAN of customer 3\"\n"
            "• \"Validate all customers\" — bulk check\n"
            "• \"Run full validation on customer 1\" — "
            "detailed report with confidence score"
        )

    # ========================================================
    # BANKING-RELATED QUESTIONS
    # ========================================================

    banking_keywords = [
        "customer", "user", "member",
        "transaction", "payment", "transfer",
        "fd", "fixed deposit", "rd",
        "recurring deposit", "share",
        "account", "onboard", "validate",
        "pan", "aadhaar", "phone",
        "balance", "deposit", "loan",
    ]

    if any(word in clean for word in banking_keywords):

        return (
            "I understand you're asking about "
            "banking information. Could you be "
            "more specific? 🤔\n\n"
            "For example:\n"
            "• \"Show customer 5\"\n"
            "• \"How many customers were created today?\"\n"
            "• \"Show transactions of customer 3\"\n"
            "• \"Validate customer 1\"\n"
            "• \"Show FD accounts\""
        )

    # ========================================================
    # YES / NO / OK
    # ========================================================

    if clean in {
        "yes", "yeah", "yep", "ok",
        "okay", "sure", "alright",
        "got it", "understood",
    }:

        return (
            "Great! 👍 What would you like "
            "to know next?"
        )

    if clean in {
        "no", "nope", "nah",
        "not really", "nothing",
    }:

        return (
            "Alright! Let me know if you need "
            "anything else. 😊"
        )

    # ========================================================
    # EMOTIONAL / SMALL TALK
    # ========================================================

    if any(
        word in clean
        for word in [
            "joke", "funny", "laugh",
            "humor", "amuse",
        ]
    ):

        return (
            "I appreciate the request! 😄 "
            "I'm better with banking data "
            "than comedy. How can I help you "
            "with E-Sahakara?"
        )

    if any(
        word in clean
        for word in [
            "weather", "news", "movie",
            "song", "game", "sport",
        ]
    ):

        return (
            "I'm specialized in E-Sahakara "
            "banking operations, so I can't help "
            "with that topic. 🏦\n\n"
            "But I can help with:\n"
            "• Customer information\n"
            "• Transactions\n"
            "• FD/RD/Share accounts\n"
            "• Validation and anomaly detection"
        )

    # ========================================================
    # DEFAULT FALLBACK
    # ========================================================

    return (
        "I'm E-Sahakara AI, your banking "
        "assistant. I'm here to help with "
        "customer information, transactions, "
        "accounts, and validation. 🏦\n\n"
        "Try asking:\n"
        "• \"Show customer 5\"\n"
        "• \"How many customers today?\"\n"
        "• \"Validate customer 1\"\n"
        "• \"Show FD accounts\"\n"
        "• \"Help\" for a full list of commands"
    )
