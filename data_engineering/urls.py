from django.urls import path

from data_engineering.api.ml import (
    predict_stock,
    prediction_monitoring,
    model_drift,
)

from data_engineering.views import (
    test_products,
    product_summary,
    price_analysis,
    business_insights,
    discount_analysis,
    rating_analysis,
    products,
)


urlpatterns = [
    path(
        "test-products/",
        test_products,
        name="test_products",
    ),

    # ML monitoring
    path(
        "ml/monitoring/",
        prediction_monitoring,
        name="prediction_monitoring",
    ),

    # ML drift detection
    path(
        "ml/drift/",
        model_drift,
        name="model_drift",
    ),

    # Product analytics
    path(
        "data/analytics/products/",
        products,
        name="analytics_products",
    ),

    path(
        "data/analytics/summary/",
        product_summary,
        name="product_summary",
    ),

    path(
        "data/analytics/price/",
        price_analysis,
        name="price_analysis",
    ),

    path(
        "data/analytics/discount/",
        discount_analysis,
        name="discount_analysis",
    ),

    path(
        "data/analytics/rating/",
        rating_analysis,
        name="rating_analysis",
    ),

    path(
        "data/analytics/business-insights/",
        business_insights,
        name="business_insights",
    ),

    # ML prediction
    path(
        "data/ml/predict/",
        predict_stock,
        name="predict_stock",
    ),
]