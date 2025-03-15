import io
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from django.conf import settings
from django.utils import timezone

def generate_order_pdf(order, user):
    """
    Generates a professional PDF for the order confirmation with:
      - Centered logo & company name
      - Clear 'Order Confirmation' heading
      - Well-structured order details with enhanced visibility
    Returns the PDF as binary data (bytes).
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    # -------------------------------------------------------
    # 1) Draw the Logo at the Center
    # -------------------------------------------------------
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo_AI_Farming_round.png")
    if os.path.exists(logo_path):
        logo_width, logo_height = 120, 120
        x, y = (width - logo_width) / 2, height - 130
        c.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # -------------------------------------------------------
    # 2) Company Name
    # -------------------------------------------------------
    c.setFont("Helvetica-Bold", 18)
    company_name = "AI Farming"
    c.drawCentredString(width / 2, height - 150, company_name)
    
    # -------------------------------------------------------
    # 3) Title: "Order Confirmation"
    # -------------------------------------------------------
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 180, "Order Confirmation")
    c.setFillColor(colors.black)
    
    # -------------------------------------------------------
    # 4) Order Details
    # -------------------------------------------------------
    left_margin = 72
    text_y = height - 220
    text_obj = c.beginText(left_margin, text_y)
    text_obj.setLeading(22)
    text_obj.setFont("Helvetica", 12)

    text_obj.textLine(f"Order Number: {order.order_number}")
    text_obj.textLine(f"Order Type: {order.get_order_type_display()}")
    text_obj.textLine(f"Order Status: {order.get_order_status_display()}")
    text_obj.textLine(f"Total Amount: ${order.total_amount:.2f} {order.currency}")
    
    # Use getattr to safely get discount_code, defaulting to None if it doesn't exist.
    discount_code = getattr(order, 'discount_code', None)
    if discount_code:
        text_obj.textLine(f"Discount Code: {discount_code}")
        
    created_str = order.created_at.strftime("%Y-%m-%d %H:%M")
    text_obj.textLine(f"Created At: {created_str}")
    
    # User Details
    text_obj.moveCursor(0, 15)  # Extra spacing
    text_obj.setFont("Helvetica-Bold", 12)
    text_obj.textLine("Customer Information")
    text_obj.setFont("Helvetica", 12)
    text_obj.textLine(f"Name: {user.username}")
    text_obj.textLine(f"Email: {user.email}")
    
    # Thank You Note
    text_obj.moveCursor(0, 20)
    text_obj.setFont("Helvetica-Oblique", 12)
    text_obj.setFillColor(colors.darkgreen)
    text_obj.textLine("Thank you for choosing AI Farming!")
    c.setFillColor(colors.black)
    
    c.drawText(text_obj)
    
    # -------------------------------------------------------
    # 5) Footer Branding
    # -------------------------------------------------------
    c.setFont("Helvetica-Oblique", 10)
    c.setFillGray(0.4)
    footer_text = "AI Farming • Empowering Smart Agriculture • www.aifarming.com"
    c.drawCentredString(width / 2, 30, footer_text)
    
    # Finalize PDF
    c.showPage()
    c.save()
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data
