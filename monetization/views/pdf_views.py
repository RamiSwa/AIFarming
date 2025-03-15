# monetization/views/pdf_views.py
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.conf import settings
from monetization.models import Order
from monetization.services.order_pdf import generate_order_pdf

def generate_order_receipt_view(request, order_id):
    """
    Generates a PDF receipt for the given order and sends it as a file download.
    """
    order = get_object_or_404(Order, id=order_id)
    pdf_data = generate_order_pdf(order, order.user)
    response = HttpResponse(pdf_data, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Order_{order.order_number}.pdf"'
    return response
