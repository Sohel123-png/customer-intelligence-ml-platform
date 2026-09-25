import math

from django.http import JsonResponse

from data_engineering.services.analytics import (
    get_business_insights,
    get_discount_analysis,
    get_price_analysis,
    get_product_dataframe,
    get_product_summary,
    get_rating_analysis,
)


def _clean_nan(obj):
    """
    Recursively replace NaN/Infinity with None.

    Empty pandas groups (e.g. a discount/rating bucket with zero products in
    it) produce NaN averages. Python's json module happily writes NaN as the
    literal token `NaN`, which is NOT valid JSON - browsers' response.json()
    then throws "Unexpected token 'N'" and the whole request fails, even
    though the HTTP response itself was 200 OK. Converting NaN -> null here
    keeps every API response valid JSON.
    """
    if isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(v) for v in obj]
    return obj


def test_products(request):
    """
    Local test data source used for ingestion testing.
    """

    products = [
        {
            "id": 1,
            "name": "Laptop",
            "category": "Electronics",
            "price": 55000,
            "source": "Demo Store",
        },
        {
            "id": 2,
            "name": "Smartphone",
            "category": "Electronics",
            "price": 25000,
            "source": "Demo Store",
        },
        {
            "id": 3,
            "name": "Running Shoes",
            "category": "Fashion",
            "price": 3500,
            "source": "Demo Store",
        },
    ]

    return JsonResponse(products, safe=False)


def product_summary(request):
    """
    Return high-level product KPIs.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    data = _clean_nan(get_product_summary())

    return JsonResponse(
        {
            "status": "success",
            "data": data,
        }
    )


def price_analysis(request):
    """
    Return product price statistics.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    data = _clean_nan(get_price_analysis())

    return JsonResponse(
        {
            "status": "success",
            "data": data,
        }
    )


def business_insights(request):
    """
    Return high-level business insights.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    data = _clean_nan(get_business_insights())

    return JsonResponse(
        {
            "status": "success",
            "data": data,
        }
    )


def discount_analysis(request):
    """
    Return discount analysis.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    df = get_discount_analysis()

    data = _clean_nan(df.reset_index().to_dict(orient="records"))

    return JsonResponse(
        {
            "status": "success",
            "data": data,
        }
    )


def rating_analysis(request):
    """
    Return rating analysis.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    df = get_rating_analysis()

    data = _clean_nan(df.reset_index().to_dict(orient="records"))

    return JsonResponse(
        {
            "status": "success",
            "data": data,
        }
    )


def products(request):
    """
    Return product analytics data.
    """

    if request.method != "GET":
        return JsonResponse(
            {
                "status": "method_not_allowed",
                "message": "Only GET requests are allowed.",
            },
            status=405,
        )

    df = get_product_dataframe()

    data = _clean_nan(df.to_dict(orient="records"))

    return JsonResponse(
        {
            "status": "success",
            "count": len(data),
            "data": data,
        }
    )