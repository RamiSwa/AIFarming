# monetization/email_service.py

from django.core.mail import EmailMessage
from django.conf import settings
from django.templatetags.static import static
from .order_pdf import generate_order_pdf


def send_report_email(pdf_path, user, location, top_crop):
    """
    Sends the generated PDF report to the user's email address using HTML formatting.
    Includes a disclaimer section at the end of the message.
    """

    # Build the logo URL from your static files
    logo_url = static("images/logo_AI_Farming.png")

    subject = f"Your AI Soil Analysis Report - {location}"

    # If no fully in-range crop is found, show a placeholder
    if not top_crop:
        top_crop = "N/A"

    # HTML email body
    body_html = f"""
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Soil Analysis Report</title>
    </head>
    <body style="font-family: Arial, sans-serif; margin: 20px;">

      <!-- Logo Section -->
      <div style="text-align: center; margin-bottom: 20px;">
        <img src="{logo_url}" 
             alt="AI Farming Logo" 
             style="width: 150px; height: auto;" />
      </div>

      <!-- Greeting -->
      <h2>Hello, {user.username}!</h2>
      <p>
        Thank you for using our <strong>premium AI-based soil analysis service</strong> 
        for your location: <strong>{location}</strong>. Please find attached your 
        detailed PDF report.
      </p>

      <!-- Top Crop Info -->
      <p>
        We noticed your top recommended crop might be: 
        <strong>{top_crop}</strong>.
      </p>

      <!-- Contact Info -->
      <p>
        If you have any questions or would like to explore more features, 
        feel free to reach us at:
        <a href="mailto:info@ramireviews.com">info@ramireviews.com</a>.
      </p>

      <!-- Sign-Off -->
      <p style="margin-top: 30px;">
        Best regards,<br/>
        <strong>Your AI Farming Team</strong>
      </p>

      <!-- Disclaimer Section -->
      <hr style="margin-top: 30px; margin-bottom: 10px;"/>
      <p style="font-size: 0.9em; color: #555;">
        <strong>Disclaimer:</strong> This AI-generated report is advisory only, 
        based on best-effort AI data. Future expansions will include deeper predictions 
        (e.g., 7–28cm soil temps). For more info, please contact 
        <a href="mailto:info@ramireviews.com">info@ramireviews.com</a>.
      </p>

    </body>
    </html>
    """

    from_email = "info@ramireviews.com"  # or settings.EMAIL_HOST_USER
    to_email = [user.email]

    email = EmailMessage(subject, body_html, from_email, to_email)
    email.content_subtype = "html"  # Send as HTML

    # Attach the PDF report
    with open(pdf_path, "rb") as f:
        email.attach("Soil_Report.pdf", f.read(), "application/pdf")

    email.send()

# monetization/email_service.py
def send_order_email(order, user):
    """
    Generates a professional order confirmation PDF and sends it via email.
    """
    # 1) Generate the PDF bytes
    pdf_content = generate_order_pdf(order, user)
    
    # Use getattr to safely retrieve discount_code, defaulting to None if it doesn't exist.
    discount_code = getattr(order, 'discount_code', None)
    discount_line = ""
    if discount_code:
        discount_line = f"<p><strong>Discount Code:</strong> {discount_code}</p>"
    
    # 2) Build an HTML email with a more "professional" layout
    subject = f"Your Order Confirmation - Order #{order.order_number}"
    logo_url = static("images/logo_AI_Farming.png")
    body_html = f"""
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Order Confirmation</title>
      <style>
        body {{
          font-family: Arial, sans-serif;
          margin: 20px;
        }}
        .header {{
          text-align: center;
          margin-bottom: 20px;
        }}
        .details {{
          font-size: 13px;
          margin: 20px 0;
        }}
        .footer {{
          text-align: center;
          font-style: italic;
          margin-top: 30px;
        }}
        .logo {{
          width: 100px;
          height: auto;
        }}
      </style>
    </head>
    <body>
      <div class="header">
        <img src="{logo_url}" alt="AI Farming Logo" class="logo">
        <h2>AI Farming</h2>
        <h3>Order Confirmation</h3>
      </div>
      <div class="details">
        <p><strong>Order Number:</strong> {order.order_number}</p>
        <p><strong>Order Type:</strong> {order.get_order_type_display()}</p>
        <p><strong>Order Status:</strong> {order.get_order_status_display()}</p>
        <p><strong>Total Amount:</strong> ${order.total_amount}</p>
        {discount_line}
        <p><strong>Currency:</strong> {order.currency}</p>
        <p><strong>Created At:</strong> {order.created_at.strftime('%Y-%m-%d %H:%M')}</p>
      </div>
      <div class="footer">
        <p>Your order has been received and processed successfully.</p>
        <p>Thank you for using our service!</p>
      </div>
    </body>
    </html>
    """

    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]
    email = EmailMessage(subject, body_html, from_email, to_email)
    email.content_subtype = "html"

    # 3) Attach the order confirmation PDF
    filename = f"Order_{order.order_number}.pdf"
    email.attach(filename, pdf_content, "application/pdf")

    email.send()
