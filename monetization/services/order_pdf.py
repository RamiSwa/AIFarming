import io
import os
import logging
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors

# Logger for debugging
logger = logging.getLogger(__name__)

def generate_order_pdf(order, user):
    """
    Generates an Order Confirmation PDF and saves it to Cloudflare R2.
    """

    # ✅ 1️⃣ Generate Cloudflare R2-compatible file path
    date_path = timezone.now().strftime("%Y/%m")  # Format: YYYY/MM
    filename = f"order_{order.order_number}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    file_path = f"orders/{user.username}/{date_path}/{filename}"  # ✅ Cloudflare R2 path

    # ✅ 2️⃣ Create the PDF in memory (NO local storage usage)
    pdf_buffer = io.BytesIO()
    c = canvas.Canvas(pdf_buffer, pagesize=letter)
    width, height = letter

    # ✅ 3️⃣ Draw the Logo at the Center
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo_AI_Farming_round.png")
    if os.path.exists(logo_path):
        logo_width, logo_height = 120, 120
        x, y = (width - logo_width) / 2, height - 130
        c.drawImage(logo_path, x, y, width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto')

    # ✅ 4️⃣ Company Name & Order Title
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 150, "AI Farming")
    
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.darkblue)
    c.drawCentredString(width / 2, height - 180, "Order Confirmation")
    c.setFillColor(colors.black)
    
    # ✅ 5️⃣ Order Details
    left_margin = 72
    text_y = height - 220
    text_obj = c.beginText(left_margin, text_y)
    text_obj.setLeading(22)
    text_obj.setFont("Helvetica", 12)

    text_obj.textLine(f"Order Number: {order.order_number}")
    text_obj.textLine(f"Order Type: {order.get_order_type_display()}")
    text_obj.textLine(f"Order Status: {order.get_order_status_display()}")
    text_obj.textLine(f"Total Amount: ${order.total_amount:.2f} {order.currency}")
    
    # ✅ Handle Discount Code (if exists)
    discount_code = getattr(order, 'discount_code', "").strip()
    if discount_code:
        text_obj.textLine(f"Discount Code: {discount_code}")
        
    created_str = order.created_at.strftime("%Y-%m-%d %H:%M")
    text_obj.textLine(f"Created At: {created_str}")
    
    # ✅ 6️⃣ User Details
    text_obj.moveCursor(0, 15)  # Extra spacing
    text_obj.setFont("Helvetica-Bold", 12)
    text_obj.textLine("Customer Information")
    text_obj.setFont("Helvetica", 12)
    text_obj.textLine(f"Name: {user.username}")
    text_obj.textLine(f"Email: {user.email}")
    
    # ✅ 7️⃣ Thank You Note
    text_obj.moveCursor(0, 20)
    text_obj.setFont("Helvetica-Oblique", 12)
    text_obj.setFillColor(colors.darkgreen)
    text_obj.textLine("Thank you for choosing AI Farming!")
    c.setFillColor(colors.black)
    
    c.drawText(text_obj)
    
    # ✅ 8️⃣ Footer Branding
    c.setFont("Helvetica-Oblique", 10)
    c.setFillGray(0.4)
    footer_text = "AI Farming • Empowering Smart Agriculture • www.aifarming.com"
    c.drawCentredString(width / 2, 30, footer_text)
    
    # ✅ 9️⃣ Finalize PDF & Save to Cloudflare R2
    c.showPage()
    c.save()
    pdf_buffer.seek(0)  # Reset buffer position

    # ✅ Save to Cloudflare R2
    saved_file_name = default_storage.save(file_path, ContentFile(pdf_buffer.getvalue()))
    file_url = f"{settings.MEDIA_URL}{saved_file_name}"  # ✅ Ensure correct URL

    # ✅ Log the saved file path & public URL
    logger.info(f"📂 Saved File Path: {saved_file_name}")
    logger.info(f"🌍 Public URL: {file_url}")

    return file_url  # ✅ Return Cloudflare R2 file URL
