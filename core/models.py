from django.db import models


class Customer(models.Model):
    PLAN_CHOICES = [("basic", "Basic"), ("pro", "Pro"), ("enterprise", "Enterprise")]
    CHANNEL_CHOICES = [("organic", "Organic"), ("paid_ads", "Paid Ads"), ("referral", "Referral"), ("partner", "Partner")]

    name = models.CharField(max_length=120)
    age = models.PositiveIntegerField()
    country = models.CharField(max_length=80)
    region = models.CharField(max_length=80)
    signup_date = models.DateField()
    plan = models.CharField(max_length=20, choices=PLAN_CHOICES)
    acquisition_channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    is_active = models.BooleanField(default=True)
    churned = models.BooleanField(default=False)
    churn_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.plan})"


class Subscription(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="subscription")
    monthly_spend = models.DecimalField(max_digits=10, decimal_places=2)
    billing_cycle = models.CharField(max_length=20, choices=[("monthly", "Monthly"), ("annual", "Annual")])
    discount_usage = models.BooleanField(default=False)
    tenure_months = models.PositiveIntegerField(default=0)


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="orders")
    order_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    product = models.CharField(max_length=120)


class Payment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="payments")
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=[("success", "Success"), ("failed", "Failed")])


class SupportTicket(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="support_tickets")
    created_date = models.DateField()
    category = models.CharField(max_length=80)
    resolved = models.BooleanField(default=True)


class ProductUsage(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="usage_logs")
    date = models.DateField()
    logins = models.PositiveIntegerField(default=0)
    features_used = models.PositiveIntegerField(default=0)


class ChurnPrediction(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="churn_prediction")
    churn_probability = models.FloatField()
    risk_level = models.CharField(max_length=10)
    top_factors = models.JSONField(default=dict)
    predicted_at = models.DateTimeField(auto_now=True)


class CustomerSegment(models.Model):
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name="segment")
    segment_name = models.CharField(max_length=60)
    cluster_id = models.IntegerField()
