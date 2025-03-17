# pages/models.py
from django.db import models
from django.conf import settings  # ✅ Reference the custom user model
import re
from django.utils.text import slugify


from django.db import models

class LandingPage(models.Model):
    """Dynamic sections of the landing page."""
    tagline = models.CharField(max_length=255, default="Smart Farming with AI - Real-Time Soil & Weather Insights")
    call_to_action = models.CharField(max_length=255, default="Get Started for Free")
    hero_image = models.ImageField(upload_to="landing_page/", blank=True, null=True)

    def get_hero_image_url(self):
        """Ensure the hero image always returns a Cloudflare R2 URL."""
        if self.hero_image:
            return f"{settings.MEDIA_URL}{self.hero_image.name}"
        return "/static/images/default-hero.png"

    def __str__(self):
        return "Landing Page Content"



class HowItWorksStep(models.Model):
    """Manage How It Works Steps dynamically."""
    landing_page = models.ForeignKey(LandingPage, on_delete=models.CASCADE, related_name="steps")
    title = models.CharField(max_length=255)
    description = models.TextField()
    icon = models.CharField(max_length=50, help_text="Example: 📍, 🤖, 📊", default="✅")
    
    
    # ✅ New Field for Dynamic Colors
    COLOR_CHOICES = [
        ("primary", "Blue"),
        ("success", "Green"),
        ("danger", "Red"),
        ("warning", "Yellow"),
        ("info", "Light Blue"),
    ]
    border_color = models.CharField(max_length=10, choices=COLOR_CHOICES, default="primary")

    def __str__(self):
        return self.title


class LandingPageFeature(models.Model):
    """Stores individual features with title and detailed content."""
    landing_page = models.ForeignKey(LandingPage, on_delete=models.CASCADE, related_name="features")
    title = models.CharField(max_length=255, help_text="Short feature title")
    description = models.TextField(help_text="Detailed feature explanation")

    def __str__(self):
        return self.title
    
    
class Testimonial(models.Model):
    """User testimonials for the homepage."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255, blank=True, null=True)
    message = models.TextField()
    image = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_published = models.BooleanField(default=True)

    def get_image_url(self):
        """Ensure the image always returns a Cloudflare R2 URL."""
        if self.image:
            return f"{settings.MEDIA_URL}{self.image.name}"
        return "/static/images/default-profile.png"

    def __str__(self):
        return f"{self.name} - {self.role}"


class ContactMessage(models.Model):
    """Stores messages sent via the contact form."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Use custom user model
    name = models.CharField(max_length=255)
    email = models.EmailField()
    subject = models.CharField(max_length=255)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} - {self.subject}"



class BlogPost(models.Model):
    """Blog articles to educate and engage users."""
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True, help_text="SEO-friendly blog URL")
    content = models.TextField()
    image = models.ImageField(upload_to="blog_images/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_published = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """Automatically generate a slug from the title if not set."""
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_image_url(self):
        """Ensure the image always returns a Cloudflare R2 URL."""
        if self.image:
            return f"{settings.MEDIA_URL}{self.image.name}"
        return "/static/images/default.png"  # ✅ Default fallback image
    
    def get_absolute_url(self):
        """Return the absolute URL for the blog post."""
        return f"/blog/{self.slug}/"

    def __str__(self):
        return self.title




class ContactInfo(models.Model):
    """Stores dynamic contact details for the Contact Page."""
    office_location = models.CharField(max_length=255, default="123 GreenField Road, AgriTech City, CA")
    phone = models.CharField(max_length=20, blank=True, null=True, default="+1 (800) 555-0199")
    email = models.EmailField(default="support@smartagritech.com")
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True, help_text="Enter WhatsApp number in international format (e.g., +18005550199)")
    additional_info = models.TextField(
        blank=True, 
        help_text="Optional extra details like support hours, alternative contact methods, or social media links."
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Contact Page Information"

    def get_whatsapp_link(self):
        """Generate a WhatsApp chat link dynamically."""
        if self.whatsapp_number:
            # Remove any non-digit characters
            cleaned_number = re.sub(r'\D', '', self.whatsapp_number)
            return f"https://wa.me/{cleaned_number}"
        return None



class AboutPage(models.Model):
    """Stores content for the About Page dynamically."""
    title = models.CharField(max_length=255, default="About AI Farming")

    # Core Content
    mission_statement = models.TextField(help_text="Describe the mission of the platform.")
    vision_statement = models.TextField(help_text="Describe the long-term vision.")

    # Founder Section
    founder_name = models.CharField(max_length=255, default="Rami Swaed")
    founder_bio = models.TextField(
        default="Founder bio will be updated soon.",
        help_text="Brief bio about the founder."
    )

    founder_image = models.ImageField(upload_to="founder_images/", blank=True, null=True, help_text="Upload a picture of the founder.")


    def get_founder_image_url(self):
        """Ensure the founder image always returns a Cloudflare R2 URL."""
        if self.founder_image:
            return f"{settings.MEDIA_URL}{self.founder_image.name}"
        return "/static/images/default-founder.png"

    def __str__(self):
        return "About Page Content"

    # Why AI Farming? Section
    why_ai_farming = models.TextField(
        default="AI Farming leverages smart analytics, real-time monitoring, and machine learning to provide farmers with actionable insights, optimizing yield and sustainability.",
        help_text="Explain why AI Farming is important."
    )
    # Our Team (Future Scalability)
    our_team = models.TextField(blank=True, help_text="Details about the team (Optional).")

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "About Page Content"


class PrivacyPolicy(models.Model):
    """Stores structured content for the Privacy Policy Page dynamically."""
    title = models.CharField(max_length=255, default="Privacy Policy")

    # Core Sections
    introduction = models.TextField(
        default="Welcome to AI Farming. Your privacy is important to us. This policy explains how we collect, use, and protect your information.",
        help_text="Introduction and overview of the privacy policy."
    )
    data_we_collect = models.TextField(
        default="We collect data such as user-provided farm details, environmental conditions, and usage data to enhance AI insights.",
        help_text="Describe the types of data collected."
    )
    how_we_use_data = models.TextField(
        default="The data collected is used to generate farming recommendations, improve AI models, and enhance user experience.",
        help_text="Explain how user data is used."
    )
    ai_data_usage = models.TextField(
        default="AI data is used solely for improving AI-driven insights and recommendations.",
        help_text="Describe how AI models use collected data."
    )
    data_sharing = models.TextField(
        default="We do not sell user data. Some data may be shared with third-party APIs for enhanced AI predictions (e.g., weather data providers).",
        help_text="Describe if and when data is shared with third parties."
    )
    user_rights = models.TextField(
        default="Users have the right to access, modify, or delete their data. Requests can be made via our contact email.",
        help_text="Explain user rights regarding their data."
    )
    data_security = models.TextField(
        default="We implement encryption, access controls, and security best practices to safeguard user data.",
        help_text="Detail security measures taken to protect user data."
    )
    cookies_policy = models.TextField(
        default="We use cookies to improve user experience. By using our platform, you agree to our cookie policy.",
        help_text="Provide details about how cookies are used on the platform."
    )
    updates_policy = models.TextField(
        default="We may update this policy periodically. Users will be notified of major changes via email or platform notifications.",
        help_text="Explain how users will be notified about policy updates."
    )
    contact_info = models.TextField(
        default="For any privacy-related concerns, contact us at support@yourdomain.com.",
        help_text="Provide contact details for privacy-related inquiries."
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Privacy Policy Content"


class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class FAQ(models.Model):
    """Manages Frequently Asked Questions dynamically."""
    question = models.CharField(max_length=255, help_text="Enter the question.")
    answer = models.TextField(help_text="Provide the answer with formatting support.")
    order = models.PositiveIntegerField(default=0, help_text="Order of appearance in the FAQ list.")
    icon = models.CharField(max_length=50, help_text="Emoji or icon to represent the question", default="❓")

    class Meta:
        ordering = ["order"]  # ✅ Ensures questions appear in the correct order

    def __str__(self):
        return self.question
