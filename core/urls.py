from django.urls import path

from . import views

# The data_engineering API is mounted once, under /api/, in config/urls.py.
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/predict/churn/", views.ChurnPredictView.as_view(), name="predict-churn"),
    path("api/customers/high-risk/", views.high_risk_customers, name="high-risk-customers"),
    path("api/customers/segments/", views.customer_segments, name="customer-segments"),
    path("api/revenue/forecast/", views.revenue_forecast, name="revenue-forecast"),
    path("api/analytics/summary/", views.analytics_summary, name="analytics-summary"),
    path("api/ask/", views.ai_business_analyst, name="ai-business-analyst"),
]
