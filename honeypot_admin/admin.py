from django.contrib import admin
from .models import FakeAdminAccessLog

@admin.register(FakeAdminAccessLog)
class FakeAdminAccessLogAdmin(admin.ModelAdmin):
    list_display = ("ip_address", "user_agent", "attempted_at")
    readonly_fields = ("ip_address", "user_agent", "attempted_at")
