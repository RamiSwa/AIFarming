from django.urls import path
from .views import (
    register_view, verify_email, login_view, logout_view, dashboard_view, 
    profile_management, delete_account, password_reset_request, password_reset_confirm, 
    resend_verification_link,  
    email_verification_success, email_verification_failed, email_verification_sent, password_reset_sent, password_reset_failed, manage_users, CustomPasswordChangeView, CustomAuthToken, api_logout_view, home_view, mark_notifications_read
)
from django.contrib.auth.views import PasswordChangeDoneView


urlpatterns = [
    
    path("", home_view, name="home"),
    
    path('api/token/', CustomAuthToken.as_view(), name='api_token_auth'),
    path('api/logout/', api_logout_view, name='api_logout'),

    path("notifications/read/", mark_notifications_read, name="mark_notifications_read"),

    path("register/", register_view, name="register"),
    path("verify-email/<uidb64>/<token>/", verify_email, name="verify_email"),
    path("login/", login_view, name="login"),
    path("logout/", logout_view, name="logout"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path("profile-management/", profile_management, name="profile_management"),
    path("delete-account/", delete_account, name="delete_account"),

    
    # ✅ Password Reset Routes
    path("password-reset/", password_reset_request, name="password_reset_request"),
    path("password-reset-confirm/<uidb64>/<token>/", password_reset_confirm, name="password_reset_confirm"),
    path("password-reset-sent/", password_reset_sent, name="password_reset_sent"),  # ✅ Fix missing route
    path("password-reset-failed/", password_reset_failed, name="password_reset_failed"),

    # ✅ Email Verification Messages
    path("email-verification-success/", email_verification_success, name="email_verification_success"),
    path("email-verification-failed/", email_verification_failed, name="email_verification_failed"),
    path("email-verification-sent/", email_verification_sent, name="email_verification_sent"),
    path("resend-verification-link/", resend_verification_link, name="resend_verification_link"),



    # ✅ Change password directly (without email)
    path("password-change/", CustomPasswordChangeView.as_view(), name="password_change"),
    path("password-change-done/", PasswordChangeDoneView.as_view(template_name="accounts/password/password_change_done.html"), name="password_change_done"),

    
    
    path("manage-users/", manage_users, name="manage_users"),

]
