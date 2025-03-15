from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.template.loader import render_to_string
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.timezone import now
from .models import UserActivity, Notification
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_protect
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from monetization.models import (
    Subscription, Order,
    Payment, AIReport,
    
    )





User = get_user_model()


def home_view(request):
    """ Redirects users to the dashboard or login page """
    if request.user.is_authenticated:
        return redirect("dashboard")  # Redirect logged-in users
    return redirect("login")  # Redirect guests to login


# ✅ Ensure `CustomAuthToken` is a class-based view (CBV)
class CustomAuthToken(ObtainAuthToken):
    """ Custom authentication view with rate limiting to prevent brute-force attacks """

    @method_decorator(ratelimit(key="ip", rate="5/m", method="POST", block=True))
    def post(self, request, *args, **kwargs):
        """ Handle token authentication """
        email = request.data.get("username")  # API expects 'username', map to email
        password = request.data.get("password")

        user = authenticate(request, email=email, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({
                'token': token.key,
                'user_id': user.id,
                'email': user.email,
            })
        return Response({"error": "Invalid credentials"}, status=400)



# ✅ API Logout View (Deletes API Token)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def api_logout_view(request):
    request.user.auth_token.delete()
    logout(request)
    return Response({"message": "Logged out successfully."}, status=200)


# ✅ Helper function for sending emails
# ✅ Helper function for sending emails
def send_email(subject, template, recipient_email, context):
    """ Sends an email using an HTML template """
    try:
        email_body = render_to_string(template, context)
        email = EmailMultiAlternatives(
            subject=subject,
            body="Click the link below.",  # Plain text fallback
            from_email=settings.EMAIL_HOST_USER,
            to=[recipient_email],
        )
        email.attach_alternative(email_body, "text/html")
        email.send()
        print(f"📩 Email sent to {recipient_email}")
    except Exception as e:
        print(f"🚨 Email sending failed: {str(e)}")
        raise Exception(f"Email sending failed: {str(e)}")  # ✅ Raise error if email fails



# ✅ Register User
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
@csrf_protect
def register_view(request):
    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        username = request.POST.get("username")
        password = request.POST.get("password")
        role = request.POST.get("role", "guest")  # Default to guest

        # ✅ Prevent users from registering as admin
        if role == "admin":
            role = "guest"  # Force default role

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect("register")

        # ✅ Enforce strong password rules
        try:
            validate_password(password)
        except ValidationError as e:
            messages.error(request, " ".join(e.messages))
            return redirect("register")

        try:
            user = User.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password
            )
            user.role = role  # ✅ Assign restricted role
            user.is_active = False
            user.save()

            # ✅ Send email verification
            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            verification_link = f"{settings.FRONTEND_URL}/accounts/verify-email/{uid}/{token}/"

            send_email(
                "Verify Your Email",
                "accounts/registration/email_verification.html",
                user.email,
                {"user": user, "verification_link": verification_link}
            )

            messages.success(request, "Registration successful! Check your email to verify your account.")
            return redirect("email_verification_sent")

        except Exception as e:
            messages.error(request, "Error creating user. Please try again.")
            return redirect("register")

    return render(request, "accounts/registration/register.html")


# ✅ Email Verification
def verify_email(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)

        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save()
            messages.success(request, "Email verified successfully!")
            return redirect("email_verification_success")

        messages.error(request, "Invalid or expired token.")
    except Exception as e:
        print(f"🚨 Email verification error: {str(e)}")
        messages.error(request, "Invalid verification link.")

    return redirect("email_verification_failed")


# ✅ Function to log user activities
def log_user_activity(user, activity_type, description=""):
    UserActivity.objects.create(user=user, activity_type=activity_type, activity_description=description, timestamp=now())


# ✅ Login User
@csrf_protect
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        user = authenticate(request, email=email, password=password)

        if user:
            if not user.is_active:
                messages.error(request, "Your account is deactivated. Please verify your email.")
                return redirect("resend_verification_link")

            login(request, user)  # ✅ This sets the session
            request.session.set_expiry(0)  # ✅ Ensure session expires when browser closes

            # ✅ Generate or get the existing auth token
            from rest_framework.authtoken.models import Token
            token, created = Token.objects.get_or_create(user=user)

            # ✅ Debugging: Print session and token info
            print("SESSIONID:", request.session.session_key)
            print("AUTH TOKEN (DRF):", token.key)

            # ✅ Response as JSON for JavaScript to handle
            response_data = {
                "message": "Login successful!",
                "authToken": token.key  # ✅ Send token in JSON
            }

            # ✅ Return JSON response instead of redirect (frontend will handle navigation)
            response = JsonResponse(response_data)
            response.set_cookie("sessionid", request.session.session_key, httponly=True, samesite="Lax")  # ✅ Session cookie


            return response

        messages.error(request, "Invalid email or password.")

    return render(request, "accounts/login.html")


# ✅ Logout User
@login_required
def logout_view(request):
    """Logs out the user and removes session & token"""
    try:
        request.user.auth_token.delete()  # ✅ Delete the auth token
    except Exception as e:
        print("Token already deleted or not found:", str(e))  # ✅ Prevent errors if token is already deleted

    logout(request)  # ✅ Logs out user (removes session)
    
    response = redirect("login")
    response.delete_cookie("sessionid")  # ✅ Remove sessionid from cookies
    messages.success(request, "Logged out successfully!")
    
    return response



# ✅ Resend Verification Link
@login_required
def resend_verification_link(request):
    """Restrict access to resending verification links to inactive users only."""

    # ✅ Prevent active users from accessing this page
    if request.user.is_active:
        messages.error(request, "Your account is already verified.")
        return redirect("dashboard")

    if request.method == "POST":
        email = request.POST.get("email")

        user = get_object_or_404(User, email=email)

        # ✅ Prevent resending if the user is already active
        if user.is_active:
            messages.error(request, "This account is already verified. No need to resend.")
            return redirect("login")

        # ✅ Rate limit: Prevent spam requests (Only allow every 10 minutes)
        last_activity = user.activities.filter(activity_type="verification_email_sent").order_by("-timestamp").first()
        if last_activity and (now() - last_activity.timestamp).seconds < 600:
            messages.warning(request, "Please wait 10 minutes before resending the verification email.")
            return redirect("email_verification_sent")

        # Generate new verification link
        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_link = f"{settings.FRONTEND_URL}/accounts/verify-email/{uid}/{token}/"

        send_email(
            "Resend: Verify Your Email",
            "accounts/registration/email_verification.html",
            user.email,
            {"user": user, "verification_link": verification_link}
        )

        log_user_activity(user, "verification_email_sent", "User requested verification email resend.")

        messages.success(request, "A new verification link has been sent to your email.")
        return redirect("email_verification_sent")

    return render(request, "accounts/registration/resend_verification_link.html")


# ✅ Password Reset Request
def password_reset_request(request):
    if request.method == "POST":
        email = request.POST.get("email")

        # ✅ Ensure the email exists in the system
        try:
            user = User.objects.get(email=email)

            # ✅ Rate limit: Prevent multiple requests in 10 minutes
            last_activity = user.activities.filter(activity_type="password_reset_requested").order_by("-timestamp").first()
            if last_activity and (now() - last_activity.timestamp).seconds < 600:
                messages.warning(request, "You can only request a password reset every 10 minutes.")
                return redirect("password_reset_sent")

            token = default_token_generator.make_token(user)
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            reset_link = f"{settings.FRONTEND_URL}/accounts/password-reset-confirm/{uid}/{token}/"

            send_email(
                "Password Reset",
                "accounts/password/password_reset_email.html",
                user.email,
                {"user": user, "reset_link": reset_link}
            )

            log_user_activity(user, "password_reset_requested", "User requested a password reset.")

            messages.success(request, "Password reset link sent to your email.")
            return redirect("password_reset_sent")

        except User.DoesNotExist:
            messages.error(request, "No account found with this email.")

    return render(request, "accounts/password/forgot_password.html")


# ✅ Password Reset Confirmation
def password_reset_confirm(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_object_or_404(User, pk=uid)

        if default_token_generator.check_token(user, token):
            if request.method == "POST":
                new_password = request.POST.get("password")

                # ✅ Enforce password validation
                try:
                    validate_password(new_password, user=user)
                except ValidationError as e:
                    messages.error(request, " ".join(e.messages))
                    return render(request, "accounts/password/password_reset_confirm.html", {"valid": True})

                user.set_password(new_password)
                user.save()
                messages.success(request, "Password reset successful! You can now login.")
                return redirect("login")

            return render(request, "accounts/password/password_reset_confirm.html", {"valid": True})

        messages.error(request, "This password reset link has already been used or has expired.")
        return redirect("password_reset_failed")

    except Exception as e:
        print(f"🚨 Password reset error: {str(e)}")
        messages.error(request, "Invalid request.")
        return redirect("password_reset_failed")


def password_reset_failed(request):
    """ Show an error message when a reset link is expired or invalid """
    messages.error(request, "The password reset link is invalid or has expired. Please request a new one.")
    return render(request, "accounts/password/password_reset_failed.html")


# ✅ User Dashboard
@login_required
def dashboard_view(request):
    user = request.user

    # ✅ Fetch User's Subscription
    subscription = Subscription.objects.filter(user=user, status="active").first()

    # ✅ Fetch User's Orders
    orders = Order.objects.filter(user=user).order_by("-created_at")

    # ✅ Fetch User's Payments
    payments = Payment.objects.filter(user=user).order_by("-created_at")

    # ✅ Fetch User's AI Reports
    ai_reports = AIReport.objects.filter(user=user).order_by("-generated_at")

    # ✅ Fetch User's Notifications (Unread first)
    notifications = Notification.objects.filter(user=user).order_by("is_read", "-created_at")[:5]

    return render(
        request,
        "accounts/dashboard.html",
        {
            "user": user,
            "subscription": subscription,
            "orders": orders,
            "payments": payments,
            "ai_reports": ai_reports,
            "notifications": notifications,  # ✅ Add notifications to the template
        },
    )

@login_required
def mark_notifications_read(request):
    """Mark all notifications as read."""
    request.user.notifications.update(is_read=True)
    return redirect("dashboard")  # Redirect back to dashboard


# ✅ API Dashboard (Token-based)
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def api_dashboard_view(request):
    return Response({"message": f"Welcome to the API dashboard, {request.user.email}!"})


# ✅ Profile Management
@login_required
def profile_management(request):
    user = request.user

    if request.method == "POST":
        # Check if profile picture is being uploaded
        if "profile_picture" in request.FILES:
            user.profile.profile_picture = request.FILES["profile_picture"]
            user.profile.save()
            messages.success(request, "Profile picture updated successfully!")
            return redirect("profile_management")

        # Otherwise, update user details
        user.first_name = request.POST.get("first_name", user.first_name)
        user.last_name = request.POST.get("last_name", user.last_name)
        user.profile.city = request.POST.get("city", user.profile.city)
        user.profile.country = request.POST.get("country", user.profile.country)

        user.save()
        user.profile.save()
        log_user_activity(user, "profile_update", "User updated profile details.")
        messages.success(request, "Profile updated successfully!")
        return redirect("profile_management")

    return render(request, "accounts/profile-management.html", {"user": user})


# ✅ Account Deletion
@login_required
def delete_account(request):
    if request.method == "POST":
        log_user_activity(request.user, "account_deletion", "User deleted their account.")
        request.user.delete()
        messages.success(request, "Account deleted successfully.")
        return redirect("register")

    return render(request, "accounts/delete_account.html")




# ✅ Email Verification Success Page
def email_verification_success(request):
    return render(request, "accounts/registration/email_verification_success.html")

# ✅ Email Verification Failed Page
def email_verification_failed(request):
    return render(request, "accounts/registration/email_verification_failed.html")

# ✅ Email Verification Sent Page
def email_verification_sent(request):
    return render(request, "accounts/registration/email_verification_sent.html")


# ✅ Password Reset Sent Page
def password_reset_sent(request):
    return render(request, "accounts/password/password_reset_sent.html")






class CustomPasswordChangeView(PasswordChangeView):
    template_name = "accounts/password/password_change.html"
    success_url = reverse_lazy("profile_management")

    def form_valid(self, form):
        messages.success(self.request, "Your password has been successfully changed!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "There was an error changing your password. Please try again.")
        return self.render_to_response(self.get_context_data(form=form))



@login_required
def manage_users(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect("dashboard")

    if request.method == "POST":
        user_id = request.POST.get("user_id")
        action = request.POST.get("action")

        user = get_object_or_404(User, id=user_id)

        # ✅ Prevent superusers from being deactivated or deleted in Manage Users
        if user.is_superuser:
            messages.error(request, "You cannot modify another admin from this panel.")
            return redirect("manage_users")

        if action == "activate":
            user.is_active = True
            log_user_activity(request.user, "user_management", f"Activated user {user.email}")
            user.save()
            messages.success(request, f"{user.email} has been activated.")

        elif action == "deactivate":
            user.is_active = False
            log_user_activity(request.user, "user_management", f"Deactivated user {user.email}")
            user.save()
            messages.warning(request, f"{user.email} has been deactivated.")

        elif action == "delete":
            log_user_activity(request.user, "user_management", f"Deleted user {user.email}")
            user.delete()
            messages.error(request, f"{user.email} has been deleted.")
            return redirect("manage_users")

    users = User.objects.all()
    return render(request, "accounts/manage_users.html", {"users": users})
