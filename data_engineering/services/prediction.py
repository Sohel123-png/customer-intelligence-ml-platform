import pandas as pd

from data_engineering.services.model_registry import (
    load_model,
    load_metadata,
)
from data_engineering.services.models import (
    CleanProduct,
    ProductPrediction,
)


def predict_next_stock(
    features: dict,
    product_id=None,
    source=None,
):
    """
    Predict next stock value using the latest trained model.

    If product_id and source are provided, the prediction
    is also saved to ProductPrediction history.
    """

    # ---------------------------------------------------------
    # 1. Load trained model and metadata
    # ---------------------------------------------------------
    try:
        model = load_model()
        metadata = load_metadata()

    except FileNotFoundError:
        return {
            "status": "model_not_ready",
            "message": "No trained model is available yet.",
        }

    # ---------------------------------------------------------
    # 2. Get required feature names
    # ---------------------------------------------------------
    feature_names = metadata["features"]

    # ---------------------------------------------------------
    # 3. Validate input features
    # ---------------------------------------------------------
    missing_features = [
        feature
        for feature in feature_names
        if feature not in features
    ]

    if missing_features:
        return {
            "status": "invalid_input",
            "message": "Required features are missing.",
            "missing_features": missing_features,
        }

    # ---------------------------------------------------------
    # 4. Prepare input DataFrame
    # ---------------------------------------------------------
    X = pd.DataFrame(
        [
            {
                feature: features[feature]
                for feature in feature_names
            }
        ]
    )

    # ---------------------------------------------------------
    # 5. Generate prediction
    # ---------------------------------------------------------
    prediction = model.predict(X)[0]

    predicted_stock = round(
        float(prediction),
        2,
    )

    # ---------------------------------------------------------
    # 6. Prepare API response
    # ---------------------------------------------------------
    response = {
        "status": "success",
        "predicted_next_stock": predicted_stock,
        "model": metadata["model_name"],
        "model_type": metadata["model_type"],
    }

    # ---------------------------------------------------------
    # 7. Save prediction history
    #
    # Product identity is:
    #     source + product_id
    #
    # This is important because different sources can have
    # the same external product ID.
    # ---------------------------------------------------------
    if product_id is not None and source is not None:

        try:
            product = CleanProduct.objects.get(
                source=source,
                product_id=str(product_id),
            )

            prediction_history = ProductPrediction.objects.create(
                product=product,
                predicted_stock=predicted_stock,
                model_name=metadata["model_name"],
                model_version=metadata.get(
                    "trained_at",
                    "unknown",
                ),
                status="pending",
            )

            response["prediction_id"] = prediction_history.id

        except CleanProduct.DoesNotExist:

            response["history_status"] = "product_not_found"

    return response