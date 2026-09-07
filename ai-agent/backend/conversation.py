# backend/conversation.py

from typing import Dict, Any, Optional
import threading


_SESSIONS: Dict[str, Dict[str, Any]] = {}

_LOCK = threading.Lock()


def create_session(session_id: str) -> Dict[str, Any]:

    with _LOCK:

        if session_id not in _SESSIONS:

            _SESSIONS[session_id] = {
                "history": [],

                "last_intent": None,

                "last_customer_id": None,

                "last_period": None,

                "last_product": None,

                "last_table": None,

                "last_customer_ids": [],

                "last_transaction_customer_id": None,

                "last_validation": None,

                "last_answer": None,
            }

        return _SESSIONS[session_id]


def get_session(session_id: str) -> Dict[str, Any]:

    return create_session(session_id)


def update_session(session_id: str, **values):

    session = create_session(session_id)

    with _LOCK:

        for key, value in values.items():

            if value is not None:
                session[key] = value


def add_message(
    session_id: str,
    role: str,
    content: str
):

    session = create_session(session_id)

    with _LOCK:

        session["history"].append({
            "role": role,
            "content": content,
        })

        # Keep the context small.
        session["history"] = session["history"][-12:]


def get_history(session_id: str):

    session = create_session(session_id)

    return list(session["history"])


def clear_session(session_id: str):

    with _LOCK:

        _SESSIONS.pop(session_id, None)


def remember_customer_ids(
    session_id: str,
    customer_ids
):

    session = create_session(session_id)

    with _LOCK:

        session["last_customer_ids"] = list(customer_ids or [])


def get_last_customer_ids(session_id: str):

    return list(
        create_session(session_id).get(
            "last_customer_ids",
            []
        )
    )