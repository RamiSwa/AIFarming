from django.contrib import admin
from .models import LandingPage, LandingPageFeature, Testimonial, ContactMessage, BlogPost, ContactInfo, AboutPage, PrivacyPolicy, NewsletterSubscriber
from django.utils.text import slugify

from .models import LandingPage, HowItWorksStep, FAQ

class HowItWorksStepInline(admin.TabularInline):  # Inline for LandingPage
    model = HowItWorksStep
    extra = 1  # Allows adding new steps from LandingPage admin.
    fields = ("icon", "title", "description", "border_color")  # ✅ Added color selection


@admin.register(LandingPage)
class LandingPageAdmin(admin.ModelAdmin):
    list_display = ('tagline', 'call_to_action') 
    list_display_links = ('tagline',) 
    list_editable = ('call_to_action',) 

    fieldsets = (
        ("Hero Section", {"fields": ("tagline", "call_to_action", "hero_image")}),
    )
    
    inlines = [HowItWorksStepInline]  # ✅ Manage "How It Works" steps from Landing Page

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ("question", "order")  # ✅ Display order in admin panel
    list_editable = ("order",)  # ✅ Allow inline editing of order
    search_fields = ("question",)  # ✅ Quick search for FAQs
    ordering = ("order",)  # ✅ Ensure they remain in correct order


@admin.register(LandingPageFeature)
class LandingPageFeatureAdmin(admin.ModelAdmin):
    list_display = ('title', 'landing_page')
    search_fields = ('title', 'description')
    list_filter = ('landing_page',)

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'is_published', 'created_at')
    list_filter = ('is_published', 'created_at')
    search_fields = ('name', 'role', 'message')
    actions = ['approve_testimonials']

    def approve_testimonials(self, request, queryset):
        queryset.update(is_published=True)

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'submitted_at')
    search_fields = ('name', 'email', 'subject')


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    """Admin panel configuration for BlogPost model."""
    
    list_display = ("title", "author", "is_published", "created_at", "updated_at")  # ✅ Show key fields in the list
    list_filter = ("is_published", "author", "created_at")  # ✅ Add filtering options
    search_fields = ("title", "content", "author__username")  # ✅ Enable search functionality
    prepopulated_fields = {"slug": ("title",)}  # ✅ Auto-fill slug from title
    ordering = ("-created_at",)  # ✅ Show latest posts first
    readonly_fields = ("created_at", "updated_at")  # ✅ Prevent manual editing of timestamps
    date_hierarchy = "created_at"  # ✅ Allow navigation by date

    fieldsets = (
        ("Basic Information", {"fields": ("title", "slug", "author", "is_published")}),
        ("Content & Media", {"fields": ("content", "image")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    def save_model(self, request, obj, form, change):
        """Ensure slug is automatically set when saving the post."""
        if not obj.slug:
            obj.slug = slugify(obj.title)
        super().save_model(request, obj, form, change)



@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ("office_location", "phone", "email", "whatsapp_number", "updated_at")
    readonly_fields = ("updated_at",)


@admin.register(AboutPage)
class AboutPageAdmin(admin.ModelAdmin):
    list_display = ("title", "founder_name", "updated_at")  # ✅ Display founder name for quick reference
    readonly_fields = ("updated_at",)  # ✅ Prevent accidental edits to timestamps
    search_fields = ("title", "founder_name")  # ✅ Allow easy searching by title and founder name
    list_filter = ("updated_at",)  # ✅ Filter by update date to track changes

    fieldsets = (
        ("General Information", {"fields": ("title", "mission_statement", "vision_statement")}),
        ("Founder Information", {"fields": ("founder_name", "founder_bio", "founder_image")}),
        ("Why AI Farming?", {"fields": ("why_ai_farming",)}),
        ("Team (Future Scalability)", {"fields": ("our_team",)}),
    )

    def has_add_permission(self, request):
        """ Prevent adding multiple About Pages (since there's usually only one). """
        return not AboutPage.objects.exists()  # ✅ Disables 'Add' if an entry exists

    def has_delete_permission(self, request, obj=None):
        """ Prevent accidental deletion of the About Page. """
        return False  # ✅ Disables delete option



@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ("title", "updated_at")  # Show title and last update time in the admin list view
    readonly_fields = ("updated_at",)  # Prevent manual editing of the update timestamp

    # Organize fields into sections for easier management
    fieldsets = (
        ("Privacy Policy Overview", {"fields": ("title", "introduction")}),
        ("Data Collection & Usage", {"fields": ("data_we_collect", "how_we_use_data", "ai_data_usage")}),
        ("Data Sharing & Security", {"fields": ("data_sharing", "user_rights", "data_security")}),
        ("Cookies & Tracking", {"fields": ("cookies_policy",)}),
        ("Policy Updates & Contact", {"fields": ("updates_policy", "contact_info")}),
        ("System Information", {"fields": ("updated_at",)}),
    )


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at")
    search_fields = ("email",)
    list_filter = ("subscribed_at",)