from django.db.models import Avg
from django.db.models.functions import Abs

from data_engineering.services.models import ProductPrediction


def get_prediction_monitoring():
    predictions = ProductPrediction.objects.all()

    total = predictions.count()

    evaluated = predictions.filter(
        status="evaluated"
    )

    pending = predictions.filter(
        status="pending"
    )

    evaluated_count = evaluated.count()

    if evaluated_count:

        mae = (
            evaluated
            .annotate(abs_error=Abs("prediction_error"))
            .aggregate(value=Avg("abs_error"))["value"]
        )

        mean_error = evaluated.aggregate(
            value=Avg("prediction_error")
        )["value"]

        errors = list(
            evaluated.values_list(
                "prediction_error",
                flat=True,
            )
        )

        rmse = (
            sum(float(error) ** 2 for error in errors)
            / len(errors)
        ) ** 0.5

    else:
        mae = None
        mean_error = None
        rmse = None

    def _serialize(prediction):
        return {
            "id": prediction.id,
            "product": prediction.product.name,
            "product_id": prediction.product.product_id,
            "predicted_stock": float(prediction.predicted_stock),
            "actual_stock": (
                float(prediction.actual_stock)
                if prediction.actual_stock is not None
                else None
            ),
            "error": (
                float(prediction.prediction_error)
                if prediction.prediction_error is not None
                else None
            ),
            "status": prediction.status,
            "model": prediction.model_name,
            "predicted_at": prediction.predicted_at.isoformat(),
        }

    # Table: most recent predictions of any status (pending or evaluated).
    recent_predictions = [
        _serialize(p) for p in predictions.select_related("product")[:10]
    ]

    # Chart: most recent EVALUATED predictions only, oldest first, so the
    # error-trend line always has points even when the newest predictions
    # are still pending (which pushes evaluated ones out of the list above).
    recent_errors = [
        _serialize(p)
        for p in evaluated.select_related("product").order_by("-predicted_at")[:20]
    ][::-1]

    return {
        "status": "success",
        "total_predictions": total,
        "evaluated_predictions": evaluated_count,
        "pending_predictions": pending.count(),
        "mae": round(float(mae), 4) if mae is not None else None,
        "rmse": round(float(rmse), 4) if rmse is not None else None,
        "mean_error": (
            round(float(mean_error), 4)
            if mean_error is not None
            else None
        ),
        "recent_predictions": recent_predictions,
        "recent_errors": recent_errors,
    }