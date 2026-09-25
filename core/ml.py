"""
Inference helpers: load trained models once, expose predict/explain functions
used by the DRF views. Run `python manage.py bootstrap_demo` (or
`generate_data` -> `train_models` -> `score_customers`) before using these.
"""
import json
from datetime import date
from functools import lru_cache

import joblib
import numpy as np
import pandas as pd
from django.conf import settings

MODEL_DIR = settings.BASE_DIR / "ml_models"


class ModelNotReadyError(RuntimeError):
    """Raised when a trained model file is missing (e.g. train_models was never run)."""


def _load(filename):
    path = MODEL_DIR / filename
    try:
        return joblib.load(path)
    except FileNotFoundError as exc:
        raise ModelNotReadyError(
            f"Model file '{filename}' not found. Run `python manage.py train_models` first."
        ) from exc


@lru_cache(maxsize=1)
def _load_churn_model():
    return _load("churn_model.joblib"), _load("churn_features.joblib")


@lru_cache(maxsize=1)
def _load_segment_model():
    return (
        _load("segment_model.joblib"),
        _load("segment_scaler.joblib"),
        _load("segment_features.joblib"),
    )


@lru_cache(maxsize=1)
def _load_revenue_model():
    return _load("revenue_model.joblib")


@lru_cache(maxsize=1)
def _get_explainer():
    """Building a SHAP TreeExplainer is expensive, so build it once per process."""
    import shap

    model, _ = _load_churn_model()
    return shap.TreeExplainer(model)


DEFAULT_SEGMENT_LABELS = {
    0: "Low Engagement",
    1: "Growth Customers",
    2: "High Value Customers",
    3: "At-Risk Customers",
}


def label_clusters(kmeans, scaler, seg_features):
    """
    KMeans cluster ids are arbitrary and change between training runs, so the
    human-readable label is derived from each cluster's profile instead of
    being hard-coded to an id.
    """
    centers = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_), columns=seg_features
    )
    remaining = set(centers.index)
    labels = {}

    high_value = int(centers.loc[list(remaining), "monthly_spend"].idxmax())
    labels[high_value] = "High Value Customers"
    remaining.discard(high_value)

    at_risk = int(centers.loc[list(remaining), "login_frequency"].idxmin())
    labels[at_risk] = "At-Risk Customers"
    remaining.discard(at_risk)

    growth = int(centers.loc[list(remaining), "total_orders"].idxmax())
    labels[growth] = "Growth Customers"
    remaining.discard(growth)

    for cluster in remaining:
        labels[int(cluster)] = "Low Engagement"
    return labels


@lru_cache(maxsize=1)
def _segment_labels():
    path = MODEL_DIR / "segment_labels.json"
    if path.exists():
        return {int(k): v for k, v in json.loads(path.read_text()).items()}
    return DEFAULT_SEGMENT_LABELS


def customer_features(customer):
    """
    Build the feature row used at training AND serving time for one Customer.

    Works with prefetched relations (support_tickets, payments, usage_logs,
    orders) so bulk scoring does not run 4+ queries per customer.
    """
    today = date.today()
    sub = customer.subscription  # raises DoesNotExist if the customer has none
    tenure = (today - customer.signup_date).days // 30
    support_count = len(customer.support_tickets.all())
    payment_failures = sum(1 for p in customer.payments.all() if p.status == "failed")
    orders = list(customer.orders.all())
    usage_logs = list(customer.usage_logs.all())
    login_frequency = int(np.mean([u.logins for u in usage_logs])) if usage_logs else 0
    days_since_last_purchase = (
        (today - max(o.order_date for o in orders)).days if orders else 999
    )

    return {
        "age": customer.age,
        "tenure_months": tenure,
        "monthly_spend": float(sub.monthly_spend),
        "total_orders": len(orders),
        "days_since_last_purchase": days_since_last_purchase,
        "support_tickets": support_count,
        "login_frequency": login_frequency,
        "payment_failures": payment_failures,
        "discount_usage": int(sub.discount_usage),
        "plan_basic": int(customer.plan == "basic"),
        "plan_pro": int(customer.plan == "pro"),
        "plan_enterprise": int(customer.plan == "enterprise"),
    }


def _risk_level(prob):
    return "HIGH" if prob >= 0.6 else "MEDIUM" if prob >= 0.3 else "LOW"


def _shap_matrix(shap_values, n_rows):
    """Normalise the different shapes SHAP returns to (rows, features) for class 1."""
    if isinstance(shap_values, list):
        return np.asarray(shap_values[1])
    values = np.asarray(shap_values)
    if values.ndim == 3:
        return values[:, :, 1]
    return values.reshape(n_rows, -1)


def predict_churn_batch(feature_dicts):
    """Predict churn probability + SHAP top factors for many rows in one go."""
    if not feature_dicts:
        return []

    model, feature_cols = _load_churn_model()
    frame = pd.DataFrame([{c: f.get(c, 0) for c in feature_cols} for f in feature_dicts])
    probs = model.predict_proba(frame)[:, 1]

    try:
        values = _shap_matrix(_get_explainer().shap_values(frame), len(frame))
    except Exception:
        values = None

    results = []
    for i, prob in enumerate(probs):
        prob = float(prob)
        top_factors = []
        if values is not None:
            contributions = sorted(
                zip(feature_cols, (float(v) for v in values[i])),
                key=lambda x: abs(x[1]),
                reverse=True,
            )[:5]
            top_factors = [{"feature": f, "impact": round(v, 4)} for f, v in contributions]
        results.append(
            {
                "churn_probability": round(prob, 4),
                "risk_level": _risk_level(prob),
                "top_factors": top_factors,
            }
        )
    return results


def predict_churn(feature_dict):
    """Predict churn probability + SHAP-based top factors for a single feature dict."""
    return predict_churn_batch([feature_dict])[0]


def assign_segment(feature_dict):
    kmeans, scaler, seg_features = _load_segment_model()
    row = pd.DataFrame([{f: feature_dict.get(f, 0) for f in seg_features}])
    cluster = int(kmeans.predict(scaler.transform(row))[0])
    return cluster, _segment_labels().get(cluster, f"Segment {cluster}")


def forecast_revenue(months_ahead=3):
    lr = _load_revenue_model()
    history_path = MODEL_DIR / "monthly_revenue_history.json"
    history = json.loads(history_path.read_text()) if history_path.exists() else []
    last_index = len(history) - 1
    forecasts = []
    for i in range(1, months_ahead + 1):
        pred = float(lr.predict(pd.DataFrame({"month_index": [last_index + i]}))[0])
        forecasts.append(round(max(pred, 0), 2))
    return {"history": history, "forecast_next_months": forecasts}
