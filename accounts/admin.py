from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count
from django.utils.html import format_html
from .models import User, UserProfile, UserActivity

class UserProfileInline(admin.StackedInline):
    """
    Inline admin descriptor for UserProfile model
    """
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profiles'
    fk_name = 'user'

class CustomUserAdmin(BaseUserAdmin):
    """
    Admin panel customization for the User model
    """
    list_display = ('email', 'username', 'first_name', 'last_name', 'status_badge', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_active', 'is_superuser')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)
    readonly_fields = ('last_login', 'date_joined')  # ✅ Ensure 'date_joined' is read-only

    fieldsets = (
        (None, {'fields': ('email', 'username', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone_number')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_admin', 'is_superuser', 'groups', 'user_permissions')}), 
        ('Important Dates', {'fields': ('last_login', 'date_joined')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )

    inlines = [UserProfileInline]  # ✅ Include the UserProfile inline

    # ✅ Allow superusers to reactivate themselves in the admin panel
    actions = ["activate_users"]

    def activate_users(self, request, queryset):
        for user in queryset:
            if user.is_superuser:  # Prevent accidental deactivation
                user.is_active = True
                user.save()
                self.message_user(request, "Selected admins have been reactivated.")
        self.message_user(request, "Selected users have been activated.")

    activate_users.short_description = "Reactivate Selected Admin Users"

    def status_badge(self, obj):
        """
        ✅ Displays a colored badge for user status in the admin panel
        """
        if obj.is_superuser:
            color, label = "#d9534f", "Superuser"
        elif obj.is_staff:
            color, label = "#f0ad4e", "Staff"
        elif obj.is_active:
            color, label = "#5cb85c", "Active"
        else:
            color, label = "#777", "Inactive"

        return format_html('<span style="background:{}; color:white; padding:5px 10px; border-radius:5px;">{}</span>', color, label)

    status_badge.short_description = "User Status"

    def changelist_view(self, request, extra_context=None):
        """
        ✅ Adds real-time total user count to the admin panel dashboard
        """
        extra_context = extra_context or {}
        extra_context['total_users'] = User.objects.count()
        extra_context['active_users'] = User.objects.filter(is_active=True).count()
        return super().changelist_view(request, extra_context=extra_context)

# ✅ Unregister User if already registered (to avoid duplicate registration)
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass  # Ignore if not registered

# ✅ Register models
admin.site.register(User, CustomUserAdmin)
admin.site.register(UserProfile)

@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'activity_type', 'activity_description', 'timestamp')
    search_fields = ('user__username', 'activity_type')
    list_filter = ('activity_type', 'timestamp')
