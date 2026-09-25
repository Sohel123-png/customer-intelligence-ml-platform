import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from faker import Faker

from core.models import Customer, Subscription, Order, Payment, SupportTicket, ProductUsage

fake = Faker()

REGIONS = {
    "India": ["Maharashtra", "Karnataka", "Delhi", "Madhya Pradesh", "Tamil Nadu", "Gujarat"],
    "USA": ["California", "Texas", "New York", "Florida"],
    "UK": ["England", "Scotland"],
}
PRODUCTS = ["Starter Pack", "Pro Suite", "Analytics Add-on", "API Access", "Premium Support"]


class Command(BaseCommand):
    help = "Generate synthetic customers, subscriptions, orders, payments, support tickets and usage logs"

    def add_arguments(self, parser):
        parser.add_argument("--customers", type=int, default=3000, help="Number of customers to generate")

    def handle(self, *args, **options):
        n = options["customers"]
        self.stdout.write(f"Generating {n} customers with related business data...")

        today = date.today()
        batch_customers = []
        countries = list(REGIONS.keys())

        for i in range(n):
            country = random.choice(countries)
            region = random.choice(REGIONS[country])
            signup_date = today - timedelta(days=random.randint(30, 900))
            plan = random.choices(["basic", "pro", "enterprise"], weights=[0.5, 0.35, 0.15])[0]
            channel = random.choice(["organic", "paid_ads", "referral", "partner"])

            # Underlying "true" churn risk drivers, used to make churn label realistic
            tenure_months = max(1, (today - signup_date).days // 30)
            base_churn_risk = 0.06
            if tenure_months < 3:
                base_churn_risk += 0.10
            support_tickets_count = random.randint(0, 12)
            if support_tickets_count > 5:
                base_churn_risk += 0.15
            payment_failures = random.randint(0, 4)
            if payment_failures > 1:
                base_churn_risk += 0.20
            login_frequency = random.randint(0, 30)
            if login_frequency < 5:
                base_churn_risk += 0.18
            if plan == "basic":
                base_churn_risk += 0.05
            if channel == "paid_ads":
                base_churn_risk += 0.03

            churned = random.random() < min(base_churn_risk, 0.9)
            churn_date = None
            is_active = True
            if churned:
                churn_date = signup_date + timedelta(days=random.randint(15, max(20, (today - signup_date).days)))
                if churn_date >= today:
                    churn_date = today - timedelta(days=random.randint(1, 20))
                is_active = False

            customer = Customer(
                name=fake.name(),
                age=random.randint(19, 62),
                country=country,
                region=region,
                signup_date=signup_date,
                plan=plan,
                acquisition_channel=channel,
                is_active=is_active,
                churned=churned,
                churn_date=churn_date,
            )
            customer._tmp = dict(
                tenure_months=tenure_months,
                support_tickets_count=support_tickets_count,
                payment_failures=payment_failures,
                login_frequency=login_frequency,
            )
            batch_customers.append(customer)

        with transaction.atomic():
            Customer.objects.bulk_create(batch_customers, batch_size=1000)

        customers = list(Customer.objects.all().order_by("-id")[:n])
        customers_by_name = {c.id: c for c in customers}

        subs, orders, payments, tickets, usage = [], [], [], [], []
        base_prices = {"basic": 499, "pro": 1999, "enterprise": 5999}

        for idx, customer in enumerate(batch_customers[::-1]):
            db_customer = customers[idx] if idx < len(customers) else None
            if db_customer is None:
                continue
            tmp = customer._tmp
            monthly_spend = base_prices[customer.plan] * random.uniform(0.85, 1.4)

            subs.append(Subscription(
                customer=db_customer,
                monthly_spend=round(monthly_spend, 2),
                billing_cycle=random.choice(["monthly", "annual"]),
                discount_usage=random.random() < 0.3,
                tenure_months=tmp["tenure_months"],
            ))

            num_orders = random.randint(1, 20)
            for _ in range(num_orders):
                order_date = customer.signup_date + timedelta(days=random.randint(0, max(1, (today - customer.signup_date).days)))
                orders.append(Order(
                    customer=db_customer,
                    order_date=order_date,
                    amount=round(random.uniform(300, 6000), 2),
                    product=random.choice(PRODUCTS),
                ))

            num_payments = random.randint(1, 15)
            for p in range(num_payments):
                pay_date = customer.signup_date + timedelta(days=random.randint(0, max(1, (today - customer.signup_date).days)))
                status = "failed" if p < tmp["payment_failures"] else "success"
                payments.append(Payment(
                    customer=db_customer,
                    payment_date=pay_date,
                    amount=round(monthly_spend, 2),
                    status=status,
                ))

            for t in range(tmp["support_tickets_count"]):
                tickets.append(SupportTicket(
                    customer=db_customer,
                    created_date=customer.signup_date + timedelta(days=random.randint(0, max(1, (today - customer.signup_date).days))),
                    category=random.choice(["billing", "technical", "onboarding", "feature_request", "bug"]),
                    resolved=random.random() < 0.85,
                ))

            for d in range(6):
                log_date = today - timedelta(days=30 * d)
                usage.append(ProductUsage(
                    customer=db_customer,
                    date=log_date,
                    logins=max(0, tmp["login_frequency"] + random.randint(-3, 3)),
                    features_used=random.randint(1, 12),
                ))

        with transaction.atomic():
            Subscription.objects.bulk_create(subs, batch_size=1000)
            Order.objects.bulk_create(orders, batch_size=2000)
            Payment.objects.bulk_create(payments, batch_size=2000)
            SupportTicket.objects.bulk_create(tickets, batch_size=2000)
            ProductUsage.objects.bulk_create(usage, batch_size=2000)

        self.stdout.write(self.style.SUCCESS(
            f"Done. {len(customers)} customers, {len(orders)} orders, {len(payments)} payments, "
            f"{len(tickets)} support tickets, {len(usage)} usage logs."
        ))
