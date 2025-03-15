from django.contrib import admin
from django.utils.timezone import now
from django.db.models import Count, Sum
from django.utils.html import format_html
from django.template.response import TemplateResponse
from django.urls import reverse


from .models import (
    Payment,
    Coupon,
    UsedCoupon,
    SubscriptionPlan,
    Subscription,
    Donation,
    PayPalConfig,
    AIReport,
    CropSuitability,
    ReportRequest,
    Order,
    Feedback,
    
)

# ✅ Custom Monetization Dashboard
class MonetizationDashboard(admin.AdminSite):
    site_header = "Monetization Admin"
    site_title = "Monetization Dashboard"
    index_title = "Financial Overview"

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path("dashboard/", self.admin_view(self.dashboard_view), name="monetization_dashboard"),
        ]
        return custom_urls + urls

    def dashboard_view(self, request):
        context = dict(
            self.each_context(request),
            total_payments=Payment.objects.count(),
            total_orders=Order.objects.count(),
            total_donations=Donation.objects.aggregate(Sum("amount"))["amount__sum"] or 0,
            total_subscriptions=Subscription.objects.count(),
        )
        return TemplateResponse(request, "admin/monetization_dashboard.html", context)


monetization_admin_site = MonetizationDashboard(name="monetization_admin")

# ✅ Register Monetization Models
monetization_admin_site.register(Payment)
monetization_admin_site.register(Order)
monetization_admin_site.register(Subscription)
monetization_admin_site.register(Donation)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "amount",
        "currency",
        "payment_method",
        "payment_type",
        "status",
        "transaction_id",
        "created_at",
        "dashboard_link",
    )
    list_filter = ("status", "payment_type", "currency", "created_at")
    search_fields = ("user__email", "transaction_id")

    def dashboard_link(self, obj):
        """✅ Fix: Hardcoded URL to avoid NoReverseMatch error"""
        return format_html('<a href="/monetization-admin/dashboard/" class="button">📊 Monetization Dashboard</a>')

    dashboard_link.short_description = "Dashboard"

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "discount_percent",
        "is_active",
        "valid_from",
        "valid_to",
        "created_at",
        "expires_at",
        "is_valid",
    )
    list_filter = ("is_active", "valid_from", "valid_to")
    search_fields = ("code",)
    
@admin.register(UsedCoupon)
class UsedCouponAdmin(admin.ModelAdmin):
    list_display = ("user", "coupon", "used_at")
    search_fields = ("user__email", "coupon__code")
    

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "price",
        "currency",
        "duration",
        "active",
        "started_at",
        "expires_at",
    )
    list_filter = ("active", "duration")
    search_fields = ("name",)



@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "subscription_id",
        "user",
        "plan",
        "start_date",
        "next_billing_date",
        "status",
    )
    list_filter = ("status", "plan")
    search_fields = ("user__email", "subscription_id")

    # ✅ Show related orders directly inside Subscription
    class OrderInline(admin.TabularInline):  
        model = Order
        extra = 0  # Prevents extra empty rows
        readonly_fields = ("order_number", "total_amount", "created_at", "receipt_url")

    inlines = [OrderInline]

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_number',
        'order_type',
        'order_status',
        'user',
        'total_amount',
        'currency',
        'created_at',
        'receipt_url',  # ✅ Added for quick access
    )
    list_filter = ('order_status', 'order_type', 'currency')
    search_fields = ('order_number', 'user__email')

    # ✅ Adding 'receipt_url' as a read-only field
    readonly_fields = ('order_number', 'created_at', 'report_url', 'report_pdf', 'receipt_url')

    fieldsets = (
        (None, {
            'fields': ('user', 'payment', 'report_request', 'order_type', 'order_status')
        }),
        ('Financial Information', {
            'fields': ('total_amount', 'discount_code', 'currency')
        }),
        ('Order Details', {
            'fields': ('order_number', 'report_url', 'report_pdf', 'receipt_url', 'created_at')  # ✅ Added 'receipt_url'
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        """Ensure key fields (like PDFs & receipts) remain readonly after creation"""
        if obj:  # If editing an existing order
            return self.readonly_fields + ('user', 'order_type', 'total_amount')
        return self.readonly_fields

    
@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ("user", "amount", "message", "created_at")
    list_filter = ("created_at",)
    search_fields = ("user__email",)
    

@admin.register(PayPalConfig)
class PayPalConfigAdmin(admin.ModelAdmin):
    list_display = ("environment", "client_id", "created_at")
    list_filter = ("environment",)
    search_fields = ("client_id",)


@admin.register(AIReport)
class AIReportAdmin(admin.ModelAdmin):
    list_display = ("user", "generated_at", "status", "expires_at", "payment")
    list_filter = ("status", "generated_at")
    search_fields = ("user__email",)





@admin.register(CropSuitability)
class CropSuitabilityAdmin(admin.ModelAdmin):
    list_display = (
        "name", "crop_type", "get_min_temp", "get_max_temp",
        "get_min_pH", "get_max_pH", "get_min_nitrogen", "get_max_nitrogen",
        "get_min_moisture", "get_max_moisture", "get_max_precipitation"
    )
    
    search_fields = ("name", "crop_type")
    ordering = ("name",)

    def get_value_from_json(self, obj, key):
        """Helper function to retrieve values from the JSON field dynamically."""
        return obj.attributes.get(key, "N/A")

    # Functions to retrieve values dynamically
    def get_min_temp(self, obj): return self.get_value_from_json(obj, "min_temp")
    def get_max_temp(self, obj): return self.get_value_from_json(obj, "max_temp")
    def get_min_pH(self, obj): return self.get_value_from_json(obj, "min_pH")
    def get_max_pH(self, obj): return self.get_value_from_json(obj, "max_pH")
    def get_min_nitrogen(self, obj): return self.get_value_from_json(obj, "min_nitrogen")
    def get_max_nitrogen(self, obj): return self.get_value_from_json(obj, "max_nitrogen")
    def get_min_moisture(self, obj): return self.get_value_from_json(obj, "min_moisture")
    def get_max_moisture(self, obj): return self.get_value_from_json(obj, "max_moisture")
    def get_max_precipitation(self, obj): return self.get_value_from_json(obj, "max_precipitation")

    # Admin display names
    get_min_temp.short_description = "Min Temp"
    get_max_temp.short_description = "Max Temp"
    get_min_pH.short_description = "Min pH"
    get_max_pH.short_description = "Max pH"
    get_min_nitrogen.short_description = "Min Nitrogen"
    get_max_nitrogen.short_description = "Max Nitrogen"
    get_min_moisture.short_description = "Min Moisture"
    get_max_moisture.short_description = "Max Moisture"
    get_max_precipitation.short_description = "Max Precipitation"






@admin.register(ReportRequest)
class ReportRequestAdmin(admin.ModelAdmin):
    list_display = (
        "user", "location", "latitude", "longitude", "soil_type",
        "get_soil_temp", "get_moisture", "get_ph_level", "get_nitrogen",
        "get_phosphorus", "get_potassium", "get_temperature", "get_humidity",
        "get_wind_speed", "get_precipitation"
    )
    search_fields = ("user__username", "location")
    readonly_fields = ("created_at", "report_data")

    def get_value_from_attributes(self, obj, key):
        """Helper function to retrieve a value from the attributes JSON field."""
        return obj.attributes.get(key, "N/A")

    def get_value_from_weather(self, obj, key):
        """Helper function to retrieve a value from the weather_data JSON field."""
        return obj.weather_data.get(key, "N/A")

    def get_soil_temp(self, obj):
        return self.get_value_from_attributes(obj, "soil_temp_0_to_7cm")
    get_soil_temp.short_description = "Soil Temp (0-7cm)"

    def get_moisture(self, obj):
        return self.get_value_from_attributes(obj, "moisture")
    get_moisture.short_description = "Moisture"

    def get_ph_level(self, obj):
        return self.get_value_from_attributes(obj, "ph_level")
    get_ph_level.short_description = "pH Level"

    def get_nitrogen(self, obj):
        return self.get_value_from_attributes(obj, "nitrogen")
    get_nitrogen.short_description = "Nitrogen"

    def get_phosphorus(self, obj):
        return self.get_value_from_attributes(obj, "phosphorus")
    get_phosphorus.short_description = "Phosphorus"

    def get_potassium(self, obj):
        return self.get_value_from_attributes(obj, "potassium")
    get_potassium.short_description = "Potassium"

    def get_temperature(self, obj):
        return self.get_value_from_weather(obj, "temperature_2m")
    get_temperature.short_description = "Temperature (2m)"

    def get_humidity(self, obj):
        return self.get_value_from_weather(obj, "relative_humidity_2m")
    get_humidity.short_description = "Humidity (2m)"

    def get_wind_speed(self, obj):
        return self.get_value_from_weather(obj, "wind_speed_10m")
    get_wind_speed.short_description = "Wind Speed (10m)"

    def get_precipitation(self, obj):
        return self.get_value_from_weather(obj, "precipitation")
    get_precipitation.short_description = "Precipitation"


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("user", "email", "feedback_text", "created_at")
    list_filter = ("created_at",)
    search_fields = ("feedback_text", "user__username", "email")
    
    
    
from django.contrib import admin
from .models import DonationOrder

class DonationOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'user', 'total_amount', 'currency', 'order_status', 'created_at')
    list_filter = ('order_status', 'currency', 'created_at')
    search_fields = ('order_number', 'user__email')
    ordering = ('-created_at',)
    readonly_fields = ('order_number', 'created_at')

    def save_model(self, request, obj, form, change):
        # The order_number is generated in the model's save() method
        super().save_model(request, obj, form, change)

admin.site.register(DonationOrder, DonationOrderAdmin)
