# ai_model/anomaly_detector.py

"""
Lightweight ML-based anomaly detector for CBS data.

Uses scikit-learn (Isolation Forest) + statistical analysis
to detect unusual patterns in customer and transaction data.

Auto-trains from the MySQL database on initialization.
CPU-only, sub-millisecond inference.
"""

import os
import re
import threading
from typing import Any, Dict, List, Optional

import numpy as np

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


# ============================================================
# CONFIGURATION
# ============================================================

# Anomaly sensitivity: how strict the detection is.
# Lower contamination = stricter (fewer anomalies).
# Higher contamination = more permissive.

SENSITIVITY_MAP = {
    "low": 0.15,
    "medium": 0.10,
    "high": 0.05,
}


# ============================================================
# ANOMALY DETECTOR
# ============================================================

class AnomalyDetector:
    """
    CBS anomaly detector.

    Learns "normal" patterns from existing database data
    and flags outliers.

    Features extracted from customer data:
    - Name length patterns
    - Phone number distribution
    - PAN/Aadhaar presence
    - Address length patterns
    - Field completeness

    Features extracted from transaction data:
    - Amount distribution
    - Frequency patterns
    """

    def __init__(
        self,
        sensitivity: str = "medium"
    ):

        contamination = SENSITIVITY_MAP.get(
            sensitivity, 0.10
        )

        self._trained = False
        self._lock = threading.Lock()

        self._scaler = None
        self._model = None

        self._stats = {
            "mean_name_length": 10.0,
            "std_name_length": 5.0,
            "mean_address_length": 30.0,
            "std_address_length": 15.0,
            "mean_phone_prefix": 8.0,
            "pan_fill_rate": 0.8,
            "aadhaar_fill_rate": 0.8,
            "field_fill_rate": 0.9,
            "total_customers": 0,
        }

        self._contamination = contamination

        # Transaction stats
        self._txn_stats = {
            "mean_amount": 10000.0,
            "std_amount": 50000.0,
            "max_amount": 1000000.0,
            "total_transactions": 0,
        }

    @property
    def is_trained(self) -> bool:
        return self._trained

    # ========================================================
    # FEATURE EXTRACTION
    # ========================================================

    def _extract_customer_features(
        self,
        customer: Dict[str, Any]
    ) -> List[float]:
        """
        Extract numeric features from a customer
        record for anomaly detection.
        """

        features = []

        # Feature 1: First name length
        first_name = str(
            customer.get("first_name") or ""
        ).strip()
        features.append(len(first_name))

        # Feature 2: Last name length
        last_name = str(
            customer.get("last_name") or ""
        ).strip()
        features.append(len(last_name))

        # Feature 3: Full name length
        features.append(
            len(first_name) + len(last_name)
        )

        # Feature 4: Phone number first digit
        phone = str(
            customer.get("phone_no") or ""
        ).strip()

        if phone and phone[0].isdigit():
            features.append(int(phone[0]))
        else:
            features.append(0)

        # Feature 5: Phone length
        phone_digits = re.sub(
            r"\D", "", phone
        )
        features.append(len(phone_digits))

        # Feature 6: PAN present (1/0)
        pan = str(
            customer.get("pan_no") or ""
        ).strip()
        features.append(
            1.0 if len(pan) == 10 else 0.0
        )

        # Feature 7: Aadhaar present (1/0)
        aadhaar = str(
            customer.get("aadhaar_no") or ""
        ).strip()
        aadhaar_digits = re.sub(
            r"\D", "", aadhaar.replace("X", "")
        )
        features.append(
            1.0
            if len(aadhaar_digits) >= 4
            else 0.0
        )

        # Feature 8: Address length
        address = str(
            customer.get("residential_address")
            or customer.get("res_address")
            or ""
        ).strip()
        features.append(len(address))

        # Feature 9: Field completeness (0.0 to 1.0)
        required = [
            "first_name",
            "last_name",
            "phone_no",
            "gender",
            "residential_address",
            "aadhaar_no",
            "pan_no",
            "status",
        ]

        filled = sum(
            1
            for field in required
            if customer.get(field)
            and str(customer[field]).strip()
        )

        features.append(
            filled / max(len(required), 1)
        )

        # Feature 10: Has relation name
        relation = str(
            customer.get("relation_name") or ""
        ).strip()
        features.append(
            1.0 if len(relation) > 0 else 0.0
        )

        return features

    # ========================================================
    # TRAINING
    # ========================================================

    def fit_from_database(
        self,
        fetch_all_func,
        db_name: str = None,
    ):
        """
        Auto-train the anomaly detector by reading
        all customers from the database.

        Parameters:
            fetch_all_func: A callable that accepts
                (sql, params) and returns List[Dict].
            db_name: Database name (unused, for future).
        """

        if not SKLEARN_AVAILABLE:

            print(
                "[AI MODEL] scikit-learn not available. "
                "Anomaly detection will use "
                "statistical fallback."
            )

            self._trained = False
            return

        try:

            rows = fetch_all_func(
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
                """,
                ()
            )

            if not rows or len(rows) < 5:

                print(
                    f"[AI MODEL] Only {len(rows or [])} "
                    "customers found. Need at least 5 "
                    "for ML training. Using statistical "
                    "fallback."
                )

                self._compute_stats(rows or [])
                self._trained = False

                return

            # Extract features
            feature_matrix = []

            for row in rows:

                features = (
                    self._extract_customer_features(row)
                )

                feature_matrix.append(features)

            X = np.array(
                feature_matrix, dtype=np.float64
            )

            # Compute basic stats
            self._compute_stats(rows)

            # Train Isolation Forest
            with self._lock:

                self._scaler = StandardScaler()

                X_scaled = self._scaler.fit_transform(X)

                self._model = IsolationForest(
                    contamination=self._contamination,
                    random_state=42,
                    n_estimators=100,
                )

                self._model.fit(X_scaled)

                self._trained = True

            print(
                f"[AI MODEL] Anomaly detector trained "
                f"on {len(rows)} customers. "
                f"Sensitivity: {self._contamination}"
            )

        except Exception as exc:

            print(
                f"[AI MODEL] Training failed: "
                f"{repr(exc)}. Using statistical "
                "fallback."
            )

            self._trained = False

    def _compute_stats(
        self,
        rows: List[Dict[str, Any]]
    ):
        """Compute basic statistics from customer data."""

        if not rows:
            return

        name_lengths = []
        address_lengths = []
        pan_count = 0
        aadhaar_count = 0

        for row in rows:

            first = str(
                row.get("first_name") or ""
            ).strip()

            last = str(
                row.get("last_name") or ""
            ).strip()

            name_lengths.append(
                len(first) + len(last)
            )

            address = str(
                row.get("residential_address")
                or row.get("res_address")
                or ""
            ).strip()

            address_lengths.append(len(address))

            pan = str(
                row.get("pan_no") or ""
            ).strip()

            if len(pan) == 10:
                pan_count += 1

            aadhaar = str(
                row.get("aadhaar_no") or ""
            ).strip()

            if len(aadhaar) >= 4:
                aadhaar_count += 1

        total = len(rows)

        self._stats = {
            "mean_name_length": (
                np.mean(name_lengths)
                if name_lengths
                else 10.0
            ),
            "std_name_length": (
                max(np.std(name_lengths), 1.0)
                if name_lengths
                else 5.0
            ),
            "mean_address_length": (
                np.mean(address_lengths)
                if address_lengths
                else 30.0
            ),
            "std_address_length": (
                max(np.std(address_lengths), 1.0)
                if address_lengths
                else 15.0
            ),
            "pan_fill_rate": (
                pan_count / total if total else 0.8
            ),
            "aadhaar_fill_rate": (
                aadhaar_count / total
                if total
                else 0.8
            ),
            "total_customers": total,
        }

    # ========================================================
    # TRAIN TRANSACTION STATS
    # ========================================================

    def fit_transaction_stats(
        self,
        fetch_all_func,
    ):
        """
        Learn transaction amount distribution
        from the database.
        """

        try:

            rows = fetch_all_func(
                """
                SELECT transaction_amount
                FROM fd_transactions
                WHERE transaction_amount IS NOT NULL
                """,
                ()
            )

            if not rows:
                return

            amounts = []

            for row in rows:

                try:
                    amt = float(
                        row.get(
                            "transaction_amount", 0
                        )
                    )

                    if amt > 0:
                        amounts.append(amt)

                except (ValueError, TypeError):
                    pass

            if amounts:

                self._txn_stats = {
                    "mean_amount": float(
                        np.mean(amounts)
                    ),
                    "std_amount": float(
                        max(np.std(amounts), 1.0)
                    ),
                    "max_amount": float(
                        np.max(amounts)
                    ),
                    "total_transactions": len(amounts),
                }

                print(
                    f"[AI MODEL] Transaction stats: "
                    f"mean=Rs.{self._txn_stats['mean_amount']:,.2f}, "
                    f"std=Rs.{self._txn_stats['std_amount']:,.2f}, "
                    f"n={len(amounts)}"
                )

        except Exception as exc:

            print(
                f"[AI MODEL] Transaction stats "
                f"failed: {repr(exc)}"
            )

    # ========================================================
    # SCORING
    # ========================================================

    def score_customer(
        self,
        customer: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Score a customer for anomalies.

        Returns:
        - anomaly_score: float (0.0 = normal, 1.0 = anomaly)
        - is_anomaly: bool
        - reasons: list of strings
        """

        result = {
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "reasons": [],
        }

        features = (
            self._extract_customer_features(customer)
        )

        # ====================================================
        # ML-based scoring (if trained)
        # ====================================================

        if self._trained and self._model and self._scaler:

            try:

                with self._lock:

                    X = np.array(
                        [features],
                        dtype=np.float64
                    )

                    X_scaled = (
                        self._scaler.transform(X)
                    )

                    # score_samples returns negative
                    # values; more negative = more anomalous
                    raw_score = (
                        self._model.score_samples(
                            X_scaled
                        )[0]
                    )

                    # Normalize to 0.0 - 1.0
                    # (more positive = more anomalous)
                    anomaly_score = max(
                        0.0,
                        min(1.0, -raw_score)
                    )

                    prediction = (
                        self._model.predict(
                            X_scaled
                        )[0]
                    )

                    is_anomaly = prediction == -1

                result["anomaly_score"] = round(
                    anomaly_score, 3
                )

                result["is_anomaly"] = is_anomaly

            except Exception:

                # Fall through to statistical
                pass

        # ====================================================
        # Statistical checks (always run)
        # ====================================================

        reasons = []

        # Check name length
        name_len = features[2]  # full name length

        mean_nl = self._stats.get(
            "mean_name_length", 10
        )
        std_nl = self._stats.get(
            "std_name_length", 5
        )

        if name_len > 0 and abs(name_len - mean_nl) > 3 * std_nl:
            reasons.append(
                "Name length is unusual compared "
                "to other customers."
            )

        # Check phone
        phone_len = features[4]

        if phone_len > 0 and phone_len != 10:
            reasons.append(
                "Phone number length deviates "
                "from standard 10 digits."
            )

        # Check address
        addr_len = features[7]

        mean_al = self._stats.get(
            "mean_address_length", 30
        )
        std_al = self._stats.get(
            "std_address_length", 15
        )

        if addr_len > 0 and abs(addr_len - mean_al) > 3 * std_al:
            reasons.append(
                "Address length is unusual compared "
                "to other customers."
            )

        # Check field completeness
        completeness = features[8]

        if completeness < 0.5:
            reasons.append(
                "Many required fields are missing."
            )

        # Check PAN presence against population
        pan_present = features[5]

        if (
            pan_present == 0
            and self._stats.get("pan_fill_rate", 0) > 0.7
        ):
            reasons.append(
                "PAN is missing — most customers "
                "have PAN on file."
            )

        # Check Aadhaar presence
        aadhaar_present = features[6]

        if (
            aadhaar_present == 0
            and self._stats.get(
                "aadhaar_fill_rate", 0
            ) > 0.7
        ):
            reasons.append(
                "Aadhaar is missing — most customers "
                "have Aadhaar on file."
            )

        result["reasons"].extend(reasons)

        # If not ML-trained, use statistical score
        if not self._trained:

            stat_score = min(
                len(reasons) * 0.2, 1.0
            )

            result["anomaly_score"] = round(
                stat_score, 3
            )

            result["is_anomaly"] = stat_score > 0.5

        return result

    # ========================================================
    # TRANSACTION SCORING
    # ========================================================

    def score_transaction_amount(
        self,
        amount: float
    ) -> Dict[str, Any]:
        """
        Score a transaction amount for anomalies.
        """

        result = {
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "reasons": [],
        }

        mean = self._txn_stats.get(
            "mean_amount", 10000
        )

        std = self._txn_stats.get(
            "std_amount", 50000
        )

        max_amt = self._txn_stats.get(
            "max_amount", 1000000
        )

        if amount <= 0:

            result["anomaly_score"] = 0.8
            result["is_anomaly"] = True
            result["reasons"].append(
                "Transaction amount is zero "
                "or negative."
            )

            return result

        # Z-score
        if std > 0:

            z_score = abs(amount - mean) / std

        else:

            z_score = 0

        if z_score > 3:

            result["anomaly_score"] = min(
                z_score / 5, 1.0
            )
            result["is_anomaly"] = True
            result["reasons"].append(
                f"Transaction amount Rs.{amount:,.2f} "
                f"is {z_score:.1f} standard deviations "
                f"from the mean (Rs.{mean:,.2f})."
            )

        elif amount > max_amt * 1.5:

            result["anomaly_score"] = 0.7
            result["is_anomaly"] = True
            result["reasons"].append(
                f"Transaction amount Rs.{amount:,.2f} "
                f"exceeds 1.5x the historical maximum "
                f"(Rs.{max_amt:,.2f})."
            )

        else:

            result["anomaly_score"] = round(
                min(z_score / 5, 0.3), 3
            )

        return result


# ============================================================
# GLOBAL DETECTOR INSTANCE
# ============================================================

_detector: Optional[AnomalyDetector] = None
_detector_lock = threading.Lock()


def get_detector(
    sensitivity: str = None,
) -> AnomalyDetector:
    """
    Get the global anomaly detector instance.
    """

    global _detector

    if sensitivity is None:

        sensitivity = os.getenv(
            "ANOMALY_SENSITIVITY",
            "medium"
        ).lower()

    with _detector_lock:

        if _detector is None:

            _detector = AnomalyDetector(
                sensitivity=sensitivity
            )

        return _detector


def initialize_detector(
    fetch_all_func,
    sensitivity: str = None,
):
    """
    Initialize and train the global detector
    from the database. Call on server startup.
    """

    detector = get_detector(sensitivity)

    detector.fit_from_database(fetch_all_func)

    detector.fit_transaction_stats(fetch_all_func)

    return detector
