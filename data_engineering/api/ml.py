import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from data_engineering.services.prediction import (
    predict_next_stock,
)

from data_engineering.services.prediction_monitoring import (
    get_prediction_monitoring,
)

from data_engineering.services.model_monitoring import (
    check_model_drift,
)


@csrf_exempt
def model_drift(request):

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
            },
            status=405,
        )

    return JsonResponse(
        check_model_drift()
    )


@csrf_exempt
def prediction_monitoring(request):
    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET is supported.",
            },
            status=405,
        )

    return JsonResponse(
        get_prediction_monitoring()
    )


@csrf_exempt
@require_POST
def predict_stock(request):
    try:
        body = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse(
            {
                "status": "invalid_json",
                "message": "Invalid JSON request.",
            },
            status=400,
        )

    if not isinstance(body, dict):
        return JsonResponse(
            {
                "status": "invalid_json",
                "message": "Request body must be a JSON object.",
            },
            status=400,
        )

    product_id = body.get("product_id")

    result = predict_next_stock(
        features=body,
        product_id=product_id,
        source=body.get("source"),
    )

    if result["status"] == "model_not_ready":
        return JsonResponse(result, status=503)

    if result["status"] == "invalid_input":
        return JsonResponse(result, status=400)

    return JsonResponse(result, status=200)
