# monetization/views/one_time_report_views.py

from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse
from decimal import Decimal
from django.utils.timezone import now
from django.conf import settings

from monetization.models import ReportRequest, SubscriptionPlan, Coupon, AIReport
from monetization.utils import has_active_subscription
from monetization.services.pdf_generator import generate_pdf
from monetization.services.email_service import send_report_email
import logging

logger = logging.getLogger(__name__)


def checkout(request):
    """
    Displays the checkout page.
    """
    report_request_id = request.session.get("report_request_id")
    if not report_request_id:
        messages.error(request, "No report request found. Please submit your request first.")
        return redirect("request_soil_report")
    try:
        report_request = ReportRequest.objects.get(id=report_request_id)
    except ReportRequest.DoesNotExist:
        messages.error(request, "Report request not found.")
        return redirect("request_soil_report")
    if request.user.is_authenticated and has_active_subscription(request.user):
        return redirect("generate_pdf_report")
    subscription_plans = SubscriptionPlan.objects.filter(active=True, duration__in=["monthly", "annual"])
    one_time_plan = SubscriptionPlan.objects.filter(duration="one_time", active=True).first()
    one_time_price = one_time_plan.price if one_time_plan else Decimal("19.99")
    available_coupons = Coupon.objects.filter(is_active=True, valid_from__lte=now(), valid_to__gte=now())
    context = {
        "report_request": report_request,
        "subscription_plans": subscription_plans,
        "one_time_price": one_time_price,
        "available_coupons": available_coupons,
    }
    return render(request, 'monetization/checkout.html', context)


def generate_pdf_report(request):
    """
    Generates the soil report PDF for one-time purchases.
    """
    report_request_id = request.session.get("report_request_id")
    if not report_request_id:
        messages.error(request, "No report request found.")
        return redirect("request_soil_report")

    try:
        report_request = ReportRequest.objects.get(id=report_request_id)
        report_data = report_request.report_data or {}

        logger.info(f"🔄 Generating PDF for user: {request.user.email}")

        # Generate PDF and get file URL
        saved_file_key, pdf_url = generate_pdf(
            report_request,
            predictions=report_data.get("predictions", {}),
            crop_details=report_data.get("crop_details", []),
            recommended_crops=report_data.get("recommended_crops", []),
            risk_assessment=report_data.get("risk_assessment", ""),
            mitigation_strategies=report_data.get("mitigation_strategies", ""),
            ai_alerts=report_data.get("ai_alerts", []),
            next_best_action=report_data.get("next_best_action", ""),
            historical_weather=report_data.get("historical_weather", {}),
            regional_avg_yield=report_data.get("regional_avg_yield", {}),
            user_data=report_data.get("user_data", {}),
            future_climate=report_data.get("future_climate", {}),
            rotation_plan=report_data.get("rotation_plan", "")
        )

        logger.info(f"✅ PDF Key: {saved_file_key}, URL: {pdf_url}")

        # Store the relative file key in the AIReport record.
        ai_report = AIReport.objects.create(
            user=request.user,
            report_file=saved_file_key,
            payment=None,
            status="completed"
        )

        logger.info(f"✅ AIReport saved for user {request.user.email}: {ai_report.report_file}")

        # Pass the full public URL to the email service.
        logger.info(f"📧 Attempting to send email to {request.user.email} with PDF: {pdf_url}")
        send_report_email(report_request, request.user, report_request.location, None, pdf_url)

        # Clear the report request from session.
        del request.session["report_request_id"]

        logger.info(f"✅ Report URL passed to template: {pdf_url}")
        return render(request, 'monetization/report_success.html', {"report_url": pdf_url})

    except Exception as e:
        logger.error(f"❌ Error generating PDF report: {str(e)}", exc_info=True)
        messages.error(request, "Error generating report. Please try again.")
        return redirect("request_soil_report")
