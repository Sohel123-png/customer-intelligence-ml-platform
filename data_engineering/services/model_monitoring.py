from data_engineering.services.models import ProductPrediction


DEFAULT_MAE_THRESHOLD = 5.0
DEFAULT_MIN_EVALUATED = 10


def check_model_drift(
    mae_threshold=DEFAULT_MAE_THRESHOLD,
    min_evaluated=DEFAULT_MIN_EVALUATED,
):
    evaluated = ProductPrediction.objects.filter(
        status="evaluated",
        prediction_error__isnull=False,
    )

    evaluated_count = evaluated.count()

    if evaluated_count < min_evaluated:
        return {
            "status": "insufficient_data",
            "drift_detected": False,
            "evaluated_predictions": evaluated_count,
            "required_predictions": min_evaluated,
            "message": (
                "Not enough evaluated predictions "
                "for reliable drift detection."
            ),
        }

    errors = [
        abs(float(error))
        for error in evaluated.values_list(
            "prediction_error",
            flat=True,
        )
    ]

    mae = sum(errors) / len(errors)

    drift_detected = mae > mae_threshold

    return {
        "status": "success",
        "drift_detected": drift_detected,
        "evaluated_predictions": evaluated_count,
        "mae": round(mae, 4),
        "mae_threshold": mae_threshold,
        "message": (
            "Model drift detected."
            if drift_detected
            else "Model performance is within threshold."
        ),
    }