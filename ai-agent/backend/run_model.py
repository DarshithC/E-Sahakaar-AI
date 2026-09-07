"""
E-Sahakara CBS Custom AI Model Runner
Run with: python run_model.py
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from database import fetch_all, fetch_one
from ai_model.anomaly_detector import initialize_detector, get_detector
from ai_model.cbs_validator import set_database_functions, validate_customer_full, validate_all_customers
from ai_model.field_validators import (
    validate_pan,
    validate_aadhaar,
    validate_phone,
    validate_ifsc,
    validate_name,
    validate_address,
)
from ai_model.response_engine import generate_response


def main():
    print("=" * 70)
    print("  E-SAHAKARA CBS CUSTOM AI MODEL — LIVE EXECUTION")
    print("=" * 70)
    print("  Architecture: 100% In-House AI / ML (Zero Ollama, Zero Cloud APIs)")
    print("=" * 70)

    # 1. FIELD VALIDATORS
    print("\n" + "-" * 70)
    print("  STEP 1: FIELD-LEVEL VALIDATORS & CHECKSUM ENGINES")
    print("-" * 70)

    test_cases = [
        ("Valid PAN (Individual)", "ABCDE1234F", validate_pan),
        ("Invalid PAN Format", "AB12345678", validate_pan),
        ("Aadhaar (Valid Verhoeff Checksum)", "234567890123", validate_aadhaar),
        ("Aadhaar (Invalid Starting Digit)", "123456789012", validate_aadhaar),
        ("Aadhaar (Masked CBS format)", "XXXX XXXX 1001", validate_aadhaar),
        ("Phone (Airtel Series)", "9876543210", validate_phone),
        ("Phone (Invalid length)", "98765", validate_phone),
        ("IFSC Code", "SBIN0001234", validate_ifsc),
    ]

    for label, val, func in test_cases:
        res = func(val)
        status_icon = "✅" if res.get("status") in ("VALID", "MASKED") else "❌"
        conf = res.get("confidence", 0)
        print(f"  {status_icon} [{res.get('status'):<8}] {label:<35} -> {val} (Conf: {conf}%)")
        print(f"     Msg: {res.get('message')}")

    # 2. ANOMALY DETECTOR
    print("\n" + "-" * 70)
    print("  STEP 2: TRAINING ISOLATION FOREST ANOMALY DETECTOR FROM CBS DATABASE")
    print("-" * 70)

    set_database_functions(fetch_all, fetch_one)
    detector = initialize_detector(fetch_all, sensitivity="medium")
    print(f"  ML Detector Trained: {detector.is_trained}")

    # 3. LIVE FULL CBS VALIDATION
    print("\n" + "-" * 70)
    print("  STEP 3: FULL CBS VALIDATION REPORT (CUSTOMER #1)")
    print("-" * 70)
    report_data = validate_customer_full(1)
    if report_data.get("success"):
        print(report_data.get("report"))
    else:
        print(f"  Failed: {report_data.get('error')}")

    # 4. BULK AUDIT
    print("\n" + "-" * 70)
    print("  STEP 4: BULK CBS AUDIT (ALL CUSTOMERS)")
    print("-" * 70)
    bulk_data = validate_all_customers()
    print(bulk_data.get("report"))

    # 5. RESPONSE ENGINE
    print("\n" + "-" * 70)
    print("  STEP 5: NATURAL LANGUAGE RESPONSE ENGINE (ZERO OLLAMA)")
    print("-" * 70)
    sample_queries = [
        "hello",
        "who are you",
        "what can you do for banking validation",
    ]
    for q in sample_queries:
        print(f"\n  Q: \"{q}\"")
        ans = generate_response(q)
        first_few = "\n".join("     " + line for line in ans.splitlines()[:4])
        print(f"{first_few}\n     ...")

    print("\n" + "=" * 70)
    print("  ALL CUSTOM AI MODEL CHECKS RAN SUCCESSFULLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
