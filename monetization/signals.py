from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.timezone import now
from .models import Payment, AIReport, ReportRequest

@receiver(post_save, sender=Payment)
def generate_ai_report(sender, instance, created, **kwargs):
    """Automatically generate an AI report when payment is completed."""
    if instance.status == "completed":
        # Check if an AI report already exists
        if not AIReport.objects.filter(payment=instance).exists():
            report_request = ReportRequest.objects.filter(user=instance.user, fulfilled=False).first()
            if report_request:
                # Mark request as fulfilled
                report_request.mark_fulfilled()

                # Create AI report
                report = AIReport.objects.create(
                    user=instance.user,
                    payment=instance,
                    report_file="reports/sample_report.pdf",  # Placeholder - Replace with actual AI-generated report
                    generated_at=now(),
                    status="completed"
                )
                print(f"✅ AI Report generated for {instance.user.username}")
