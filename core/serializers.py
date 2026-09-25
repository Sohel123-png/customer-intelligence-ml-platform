from rest_framework import serializers
from .models import Customer, Subscription


class CustomerSerializer(serializers.ModelSerializer):
    monthly_spend = serializers.SerializerMethodField()

    class Meta:
        model = Customer
        fields = ["id", "name", "age", "country", "region", "plan", "acquisition_channel",
                  "signup_date", "is_active", "churned", "monthly_spend"]

    def get_monthly_spend(self, obj):
        try:
            return float(obj.subscription.monthly_spend)
        except Subscription.DoesNotExist:
            return None


class ChurnPredictInputSerializer(serializers.Serializer):
    customer_id = serializers.IntegerField(required=False)
    age = serializers.IntegerField(required=False, default=35)
    tenure_months = serializers.IntegerField(required=False, default=12)
    monthly_spend = serializers.FloatField(required=False, default=1500)
    total_orders = serializers.IntegerField(required=False, default=5)
    days_since_last_purchase = serializers.IntegerField(required=False, default=30)
    support_tickets = serializers.IntegerField(required=False, default=1)
    login_frequency = serializers.IntegerField(required=False, default=15)
    payment_failures = serializers.IntegerField(required=False, default=0)
    discount_usage = serializers.IntegerField(required=False, default=0)
    plan = serializers.ChoiceField(choices=["basic", "pro", "enterprise"], required=False, default="pro")
