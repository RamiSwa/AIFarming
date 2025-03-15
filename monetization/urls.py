# monetization/urls.py
from django.urls import path
from monetization.views.subscription_views import (
    subscription_pricing, process_subscription, cancel_subscription, subscription_renewal
)
from monetization.views.one_time_report_views import checkout, generate_pdf_report
from monetization.views.payment_views import process_payment, payment_success
from monetization.views.paypal_webhook import paypal_webhook
from monetization.views.donation_views import donation_page, process_donation, donation_success
from monetization.views.pdf_views import generate_order_receipt_view
from monetization.views.api_views import (
    RequestReportView, CropSuitabilityView, RiskAssessmentView,
    AIAlertsView, MitigationStrategiesView, NextBestActionView, FeedbackView,
    request_soil_report, overall_report, crop_suitability_page,
    risk_assessment_page, ai_alerts_page, next_best_action_page,
    ReportStatusView,  
)

urlpatterns = [
    path('request-soil-report/', request_soil_report, name='request_soil_report'),
    path('checkout/', checkout, name='checkout'),
    path('process-payment/', process_payment, name='process_payment'),
    path('process-subscription/', process_subscription, name='process_subscription'),
    path('payment-success/', payment_success, name='payment_success'),
    path('webhook/', paypal_webhook, name='paypal_webhook'),
    path('generate-pdf/', generate_pdf_report, name='generate_pdf_report'),
    path("pricing/", subscription_pricing, name="subscription_pricing"),
    path("cancel-subscription/<str:subscription_id>/", cancel_subscription, name="cancel_subscription"),
    path("subscription-renewal/", subscription_renewal, name="subscription_renewal"),
    # API endpoints
    path("api/request-report/", RequestReportView.as_view(), name="request-report"),
    path('api/crop-suitability/', CropSuitabilityView.as_view(), name='crop-suitability'),
    path('api/risk-assessment/', RiskAssessmentView.as_view(), name='risk-assessment'),
    path('api/ai-alerts/', AIAlertsView.as_view(), name='ai-alerts'),
    path('api/mitigation-strategies/', MitigationStrategiesView.as_view(), name='mitigation-strategies'),
    path('api/next-best-action/', NextBestActionView.as_view(), name='next-best-action'),
    path("api/feedback/", FeedbackView.as_view(), name="feedback"),
    path("api/report-status/", ReportStatusView.as_view(), name="report-status"),

    path("overall-report/", overall_report, name="overall_report"),
    path("crop-suitability/", crop_suitability_page, name="crop_suitability_page"),
    path("risk-assessment/", risk_assessment_page, name="risk_assessment_page"),
    path("ai-alerts/", ai_alerts_page, name="ai_alerts_page"),
    path("next-best-action/", next_best_action_page, name="next_best_action_page"),
    # Donation views
    path("donation/", donation_page, name="donation_page"),
    path("process-donation/", process_donation, name="process_donation"),
    path("donation-success/", donation_success, name="donation_success"),
    # Order receipt (PDF) download view
    path("order-receipt/<int:order_id>/", generate_order_receipt_view, name="order_receipt"),
]
