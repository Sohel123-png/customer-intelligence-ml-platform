from django.contrib import admin
from .models import (
    Customer, Subscription, Order, Payment, SupportTicket,
    ProductUsage, ChurnPrediction, CustomerSegment,
)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("name", "plan", "region", "country", "churned", "is_active", "signup_date")
    list_filter = ("plan", "region", "churned", "is_active")
    search_fields = ("name",)


admin.site.register(Subscription)
admin.site.register(Order)
admin.site.register(Payment)
admin.site.register(SupportTicket)
admin.site.register(ProductUsage)


@admin.register(ChurnPrediction)
class ChurnPredictionAdmin(admin.ModelAdmin):
    list_display = ("customer", "churn_probability", "risk_level", "predicted_at")
    list_filter = ("risk_level",)


@admin.register(CustomerSegment)
class CustomerSegmentAdmin(admin.ModelAdmin):
    list_display = ("customer", "segment_name", "cluster_id")
    list_filter = ("segment_name",)
