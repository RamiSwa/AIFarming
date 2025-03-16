
# monetization/models.py

from django.db import models
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
from django.utils import timezone

from django.core.files.base import ContentFile
from monetization.services.order_pdf import generate_order_pdf


from accounts.utils import send_notification
from django.core.files.storage import default_storage




class Payment(models.Model):
    """Tracks payments for AI reports (PayPal only) across one-time, subscription & donation options."""
    PAYMENT_TYPES = [
        ("one_time", "One-Time Purchase"),
        ("subscription", "Subscription"),
        ("donation", "Donation"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    payment_method = models.CharField(max_length=50, choices=[
        ("paypal", "PayPal"),
    ])
    payment_type = models.CharField(max_length=20, choices=PAYMENT_TYPES, default="one_time")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    transaction_id = models.CharField(max_length=255, blank=True, null=True, unique=True)
    receipt_url = models.URLField(blank=True, null=True)  # PayPal receipt link
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_code = models.CharField(max_length=50, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        """
        Auto-mark as 'completed' when a transaction_id is provided,
        but skip auto-completion for donation payments.
        """
        if self.transaction_id and self.status == "pending" and self.payment_type != "donation":
            self.status = "completed"
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Payment {self.id} - {self.status} - {self.user.email}"
    

def process_payment(payment):
    if payment.status == "failed":
        send_notification(payment.user, "🚨 Your payment failed. Please update your billing details.", "payment")


class Coupon(models.Model):
    """Stores discount coupon codes for admin-managed pricing discounts."""
    code = models.CharField(max_length=50, unique=True)
    discount_percent = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Enter discount as a percentage (e.g., 50.00 for 50% off)."
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()

    @property
    def is_valid(self):
        """Automatically deactivate expired coupons."""
        return self.is_active and (self.valid_from <= now() <= self.valid_to)

    def __str__(self):
        return f"Coupon {self.code} - {self.discount_percent}% off"
    
    
class UsedCoupon(models.Model):
    """Tracks coupon usage per user."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE)
    used_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Coupon {self.coupon.code} used by {self.user.email}"
    
    
class SubscriptionPlan(models.Model):
    """Defines a subscription plan with fixed pricing."""
    DURATION_CHOICES = [
        ("one_time", "One-Time"),
        ("monthly", "Monthly"),
        ("annual", "Annual"),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default="USD")
    description = models.TextField(blank=True, null=True)
    duration = models.CharField(max_length=10, choices=DURATION_CHOICES, default="one_time")
    active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    paypal_plan_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Enter the PayPal plan ID for this subscription plan."
    )

    def __str__(self):
        return f"Plan: {self.name} - {self.price} {self.currency} ({self.duration})"




class Subscription(models.Model):
    STATUS_CHOICES = [
        ("active", "Active"),
        ("canceled", "Canceled"),
        ("paused", "Paused"),
        ("expired", "Expired"),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey('SubscriptionPlan', on_delete=models.CASCADE)
    payment = models.OneToOneField('Payment', on_delete=models.CASCADE, blank=True, null=True)
    subscription_id = models.CharField(max_length=255, unique=True, help_text="PayPal subscription ID")
    start_date = models.DateTimeField(auto_now_add=True)
    next_billing_date = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="active")

    def renew_subscription(self):
        """Automatically creates an order & receipt when PayPal renews the subscription."""
        order = Order.objects.create(
            user=self.user,
            order_type="subscription",
            total_amount=self.plan.price,
            currency="USD",
            order_status="completed",
            payment=None
        )
        order.generate_receipt()


    def __str__(self):
        return f"Subscription {self.subscription_id} for {self.user.email}"


def check_expiring_subscriptions():
    expiring_soon = Subscription.objects.filter(next_billing_date__lte=now() + timedelta(days=3), status="active")
    for sub in expiring_soon:
        send_notification(sub.user, "⚠️ Your subscription is expiring in 3 days! Renew now to avoid service interruption.", "subscription")



class Order(models.Model):
    ORDER_TYPES = [
        ('one_time', 'One-Time Purchase'),
        ('subscription', 'Subscription'),
        ('donation', 'Donation'),
    ]
    ORDER_STATUSES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE, null=True, blank=True)
    report_request = models.ForeignKey('ReportRequest', on_delete=models.SET_NULL, null=True, blank=True)
    subscription = models.ForeignKey('Subscription', on_delete=models.SET_NULL, null=True, blank=True)
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES)
    order_status = models.CharField(max_length=20, choices=ORDER_STATUSES, default="pending")
    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_code = models.CharField(max_length=50, blank=True, null=True)
    currency = models.CharField(max_length=10, default="USD")
    created_at = models.DateTimeField(auto_now_add=True)
    report_url = models.URLField(blank=True, null=True)
    receipt_url = models.URLField(blank=True, null=True)  # ✅ PayPal receipt link

    report_pdf = models.FileField(upload_to="orders_pdfs/", blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            super().save(*args, **kwargs)
            self.order_number = f"ORD-{timezone.now().strftime('%Y%m%d')}-{self.pk:04d}"
            Order.objects.filter(pk=self.pk).update(order_number=self.order_number)

        if not self.report_pdf:
            self.generate_receipt()

        super().save(*args, **kwargs)

    def generate_receipt(self):
        """Generates a receipt PDF & stores the URL."""
        pdf_data = generate_order_pdf(self, self.user)
        self.report_pdf.save(f"{self.order_number}.pdf", ContentFile(pdf_data), save=False)
        self.receipt_url = default_storage.url(self.report_pdf.name)
        self.save()

    def __str__(self):
        return f"Order {self.order_number} - {self.order_type} for {self.user.email}"



def has_active_subscription(user):
    """Check if user has an active subscription OR if it's canceled but still within the billing period."""
    return Subscription.objects.filter(
        user=user,
        status__in=["active", "canceled"],  # ✅ Allow "canceled" but still valid
        next_billing_date__gte=now()  # ✅ User has access until their next billing date
    ).exists()

    

class Donation(models.Model):
    """Allows users to donate to support AI farming research."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Donation - ${self.amount} by {self.user.email if self.user else 'Anonymous'}"


class PayPalConfig(models.Model):
    """Stores PayPal API credentials (Sandbox & Live) for easy switching."""
    environment = models.CharField(max_length=10, choices=[
        ("sandbox", "Sandbox (Trial)"),
        ("live", "Live (Production)"),
    ], default="sandbox")
    client_id = models.CharField(max_length=255)
    secret_key = models.CharField(max_length=255)
    webhook_secret = models.CharField(max_length=255, blank=True, null=True)  # NEW FIELD
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"PayPal Config - {self.environment}"




class AIReport(models.Model):
    """Stores AI-generated land reports after successful payment."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    report_file = models.FileField(upload_to="reports/")
    generated_at = models.DateTimeField(auto_now_add=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ], default="processing")
    expires_at = models.DateTimeField(blank=True, null=True)

    def save(self, *args, **kwargs):
        """Ensure one-time purchases expire but subscriptions stay valid."""
        if not self.expires_at and (self.payment is None or self.payment.payment_type == "one_time"):
            self.expires_at = now() + timedelta(days=7)
        elif self.payment and self.payment.payment_type == "subscription":
            self.expires_at = None  # Subscriptions never expire
        super().save(*args, **kwargs)



    def __str__(self):
        return f"Report for {self.user.username} - {self.generated_at}"
    
def generate_ai_report(report):
    report.status = "completed"
    report.save()
    send_notification(report.user, f"📄 Your AI report generated on {report.generated_at.strftime('%B %d, %Y')} is ready for download.", "ai_report")



class ReportRequest(models.Model):
    """Stores user requests for AI Soil Reports with dynamic soil attributes."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    # ✅ Location Details
    location = models.CharField(max_length=200)
    original_location = models.CharField(max_length=100, blank=True, null=True)
    latitude = models.FloatField(default=0.0)
    longitude = models.FloatField(default=0.0)

    # ✅ Soil Data (DYNAMIC STORAGE)
    attributes = models.JSONField(default=dict, blank=True, help_text="Dynamic soil properties (e.g., pH, nitrogen, moisture).")

    # ✅ Weather Data
    weather_data = models.JSONField(default=dict, blank=True, help_text="Dynamic weather data (e.g., temperature, humidity, wind speed).")

    # ✅ Additional Farming Details
    crop_type = models.CharField(max_length=100, blank=True, null=True)
    irrigation_method = models.CharField(max_length=100, blank=True, null=True)
    additional_notes = models.TextField(blank=True, null=True)
    soil_type = models.CharField(max_length=100, blank=True, null=True)
    report_data = models.JSONField(default=dict, blank=True, help_text="Processed data for PDF generation")

    # ✅ Status Tracking
    fulfilled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def mark_fulfilled(self):
        """Marks report request as fulfilled when AIReport is generated."""
        self.fulfilled = True
        self.save()

    def __str__(self):
        return f"Report Request - {self.user.username} ({self.location})"


class CropSuitability(models.Model):
    """Stores crop growth conditions dynamically."""
    name = models.CharField(max_length=100, unique=True)
    crop_type = models.CharField(max_length=100, blank=True, null=True)

    # ✅ Dynamic Storage for Crop Conditions
    attributes = models.JSONField(default=dict, blank=True, help_text="Dynamic crop suitability conditions (e.g., min_temp, max_pH).")

    # ✅ Soil Type Compatibility
    suitable_soil_types = models.JSONField(default=list, blank=True, help_text="List of suitable soil types.")

    # ✅ Growing Season
    preferred_growing_season = models.JSONField(default=list, blank=True, help_text="List of preferred growing months [1-12].")

    def __str__(self):
        return self.name


class Feedback(models.Model):
    """
    Stores user feedback for the AI Soil Report service.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        blank=True, 
        null=True
    )
    email = models.EmailField(blank=True, null=True)
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.user:
            return f"Feedback from {self.user.username} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"
        return f"Feedback from {self.email} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"



class DonationOrder(models.Model):
    ORDER_TYPES = (
        ('donation', 'Donation'),
    )
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    payment = models.ForeignKey('Payment', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    currency = models.CharField(max_length=10, default="USD")
    order_status = models.CharField(
        max_length=20,
        choices=[('pending', 'Pending'), ('completed', 'Completed'), ('cancelled', 'Cancelled')],
        default="completed"
    )
    order_type = models.CharField(max_length=20, choices=ORDER_TYPES, default="donation")
    order_number = models.CharField(max_length=50, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # If new, save once to get a primary key
        if not self.pk:
            super().save(*args, **kwargs)
            # Generate the order number using the newly created primary key
            self.order_number = f"DON-{timezone.now().strftime('%Y%m%d')}-{self.pk:04d}"
            DonationOrder.objects.filter(pk=self.pk).update(order_number=self.order_number)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        return f"DonationOrder {self.order_number} for {self.user.email}"