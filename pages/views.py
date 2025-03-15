from django.shortcuts import get_object_or_404, render, redirect
from .models import LandingPage, Testimonial, ContactInfo, ContactMessage, BlogPost, AboutPage, PrivacyPolicy, NewsletterSubscriber, FAQ
from django.contrib import messages
from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags


from django.utils import timezone
from monetization.models import SubscriptionPlan, Coupon

def landing_page_view(request):
    """Fetch dynamic content for the Landing Page, including pricing plans."""
    landing_page = LandingPage.objects.first()
    testimonials = Testimonial.objects.filter(is_published=True).order_by("-created_at")
    faqs = FAQ.objects.all()  # ✅ Load all FAQs
    # Fetch active subscription plans
    subscription_plans = SubscriptionPlan.objects.filter(active=True)

    # Fetch active and valid coupons
    available_coupons = Coupon.objects.filter(
        is_active=True, 
        valid_from__lte=timezone.now(), 
        valid_to__gte=timezone.now()
    )

    return render(request, "pages/landing_page.html", {
        "landing_page": landing_page,
        "testimonials": testimonials,
        "subscription_plans": subscription_plans,  # ✅ Now passed to template
        "available_coupons": available_coupons,
        "faqs": faqs
    })







def contact_view(request):
    """Fetch contact details dynamically and handle form submissions."""
    contact_info = ContactInfo.objects.first()  # Get the first entry

    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        subject = request.POST.get("subject")
        message = request.POST.get("message")

        if name and email and subject and message:
            # Save the contact message to the database
            ContactMessage.objects.create(name=name, email=email, subject=subject, message=message)

            # Prepare email notification content for admin
            admin_email_subject = f"New Contact Message: {subject}"
            admin_email_body = (
                f"You have received a new message from {name} ({email}).\n\n"
                f"Message:\n{message}"
            )
            # Send the notification email to the admin
            send_mail(
                admin_email_subject,
                admin_email_body,
                settings.EMAIL_HOST_USER,
                [settings.CONTACT_NOTIFICATION_EMAIL],
                fail_silently=False,
            )

            # Prepare the confirmation email for the customer
            customer_subject = "Thank you for contacting us!"
            # Render the HTML email template
            html_content = render_to_string("email/contact_confirmation.html", {
                "name": name,
                "message": message,
                "contact_info": contact_info,  # You can include additional info if desired
            })
            # Create a plain text version by stripping HTML tags
            text_content = strip_tags(html_content)
            # Create the email message with both plain text and HTML parts
            email_message = EmailMultiAlternatives(
                customer_subject,
                text_content,
                settings.EMAIL_HOST_USER,
                [email],
            )
            email_message.attach_alternative(html_content, "text/html")
            email_message.send()

            messages.success(request, f"✅ Thank you, {name}! Your message has been received. We'll get back to you as soon as possible.")
            
            # Redirect to avoid re-submission on refresh
            return redirect(request.path_info)
        else:
            messages.error(request, "All fields are required.")

    return render(request, "pages/contact.html", {"contact_info": contact_info})



def subscribe_view(request):
    """Handle newsletter subscription form submission and send a confirmation email."""
    if request.method == "POST":
        email = request.POST.get("email")
        if email:
            subscriber, created = NewsletterSubscriber.objects.get_or_create(email=email)
            if created:
                messages.success(request, "Thanks for subscribing to our newsletter!")
                
                # Prepare and send the confirmation email
                subject = "Subscription Confirmation"
                confirmation_message = (
                    "Thank you for subscribing to our newsletter! "
                    "You'll receive the latest updates on AI-driven agriculture."
                )
                send_mail(
                    subject,
                    confirmation_message,
                    settings.EMAIL_HOST_USER,
                    [email],
                    fail_silently=False,
                )
            else:
                messages.info(request, "You're already subscribed to our newsletter.")
        else:
            messages.error(request, "Please provide a valid email address.")
    return redirect(request.META.get("HTTP_REFERER", "/"))





def blog_list_view(request):
    """Fetch published blog posts."""
    blog_posts = BlogPost.objects.filter(is_published=True).order_by("-created_at")
    return render(request, "pages/blog_list.html", {"blog_posts": blog_posts})

def blog_detail_view(request, slug):
    """Fetch a single blog post by its slug, and related posts."""
    blog_post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    
    # Fetch 3 related posts (excluding the current post)
    related_posts = BlogPost.objects.filter(is_published=True).exclude(slug=slug).order_by('-created_at')[:3]

    return render(request, "pages/blog_detail.html", {"blog_post": blog_post, "related_posts": related_posts})



def about_page_view(request):
    """Fetch dynamic content for the About Page."""
    about_page = AboutPage.objects.first()  # Assuming only one entry exists

    return render(request, "pages/about.html", {
        "about_page": about_page
    })




def privacy_policy_view(request):
    """Fetch dynamic content for the Privacy Policy Page."""
    privacy_policy = PrivacyPolicy.objects.first()  # Assuming only one entry exists

    return render(request, "pages/privacy_policy.html", {
        "privacy_policy": privacy_policy
    })
