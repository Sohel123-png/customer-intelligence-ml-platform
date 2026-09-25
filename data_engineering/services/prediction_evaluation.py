from django.db import transaction

from data_engineering.services.models import (
    ProductPrediction,
    ProductSnapshot,
)


def evaluate_pending_prediction(snapshot: ProductSnapshot):
    """
    Evaluate the most recent pending prediction for a product
    using the newly arrived product snapshot as the actual value.
    """

    prediction = (
        ProductPrediction.objects
        .filter(
            product=snapshot.product,
            status="pending",
            predicted_at__lt=snapshot.captured_at,
        )
        .order_by("-predicted_at")
        .first()
    )

    if prediction is None:
        return {
            "status": "no_pending_prediction",
            "evaluated": False,
        }

    actual_stock = float(snapshot.stock)
    predicted_stock = float(prediction.predicted_stock)

    prediction.actual_stock = actual_stock
    prediction.prediction_error = (
        actual_stock - predicted_stock
    )
    prediction.status = "evaluated"

    prediction.save(
        update_fields=[
            "actual_stock",
            "prediction_error",
            "status",
        ]
    )

    return {
        "status": "evaluated",
        "evaluated": True,
        "prediction_id": prediction.id,
        "predicted_stock": predicted_stock,
        "actual_stock": actual_stock,
        "prediction_error": prediction.prediction_error,
    }