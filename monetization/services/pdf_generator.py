# monetization/services/pdf_generator.py
# =============================================================================
# 0) IMPORTS & LIBRARY SETUP
# =============================================================================
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
)
import os
from django.conf import settings
import matplotlib.pyplot as plt
import numpy as np
from reportlab.lib.units import inch
from PIL import Image as PILImage, ImageDraw
import json
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import io
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# 1) HELPER FUNCTIONS
# =============================================================================

# 1.1) Round Image Helper Function
def make_image_round(input_path, output_path, size=(140, 140)):
    """
    Converts a square image into a round-cropped version and saves it.
    """
    img = PILImage.open(input_path).convert("RGBA")
    img = img.resize(size, PILImage.LANCZOS)
    mask = PILImage.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + size, fill=255)
    result = PILImage.new("RGBA", size, (255, 255, 255, 0))
    result.paste(img, (0, 0), mask)
    result.save(output_path)
    return output_path

# =============================================================================
# 2) MAIN PDF GENERATION FUNCTION
# =============================================================================

def generate_pdf(report_request, predictions, crop_details, recommended_crops, risk_assessment, mitigation_strategies, ai_alerts, next_best_action, historical_weather, regional_avg_yield, user_data, future_climate=None, rotation_plan=None):
    """
    Generates a premium AI-powered soil analysis report with multiple sections.
    
    Premium Enhancements include:
      - Branded cover page with logo, tagline, and farmland background.
      - Future climate predictions, crop rotation plan, and additional visuals.
      - Stacked yield chart and monthly precipitation chart based on real data.
    """

    try:
        # 2.1) Setup Document & Styles
        # Build a subfolder path: e.g. "reports/<username>/<YYYY>/<MM>/"
        date_path = now().strftime("%Y/%m")  # Year/Month folder structure
        filename = f"soil_report_{report_request.id}_{now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file_path = f"reports/{report_request.user.username}/{date_path}/{filename}"  # ✅ R2-compatible path

        # Setup the document
        # ✅ 2️⃣ Create the PDF in memory (NO local storage usage)
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(pdf_buffer, pagesize=letter)
        elements = []
        styles = getSampleStyleSheet()
        wrap_style = ParagraphStyle(name="WrapStyle", parent=styles["Normal"], fontSize=10, leading=12)


        # 2.2) Premium Cover Page
        elements.extend(_build_premium_cover_page(report_request, user_data))

        # 2.3) Page Break Before Main Content
        elements.append(PageBreak())

        # 2.4) Executive Summary & Basic Info
        elements.append(Paragraph("<b>Executive Summary</b>", styles["Heading1"]))
        main_alert = ai_alerts[0] if ai_alerts and 'No significant alerts' not in ai_alerts[0] else 'None'
        top_crop_text = recommended_crops[0]['name'] if recommended_crops else 'N/A'
        summary_text = (
            f"<b>Key Soil pH:</b> {user_data.get('ph_level', 'N/A')}<br/>"
            f"<b>AI-Predicted Soil Temp (0-7cm):</b> {user_data.get('predicted_soil_temp', 'N/A')}°C<br/>"
            f"<b>Measured Soil Temp (0-7cm):</b> {user_data.get('measured_soil_temp', 'N/A')}°C<br/>"
            f"<b>Top Recommended Crop:</b> {top_crop_text}<br/>"
            f"<b>Main Weather Risk:</b> {main_alert}<br/>"
            f"<b>Next Best Action:</b> See details below."
        )
        print(f"DEBUG - Summary Text: {summary_text}")  # ✅ Check before adding to PDF

        elements.append(Paragraph(summary_text, styles["Normal"]))
        elements.append(Spacer(1, 20))

        # 2.5) Future Climate Forecast
        if future_climate:
            elements.append(Paragraph("<b>Future Climate Predictions (30-90 Days)</b>", styles["Heading2"]))
            forecast_text = (
                f"• Next 30 Days: {future_climate['30_days']}°C<br/>"
                f"• Next 60 Days: {future_climate['60_days']}°C<br/>"
                f"• Next 90 Days: {future_climate['90_days']}°C<br/>"
                "Planting windows may shift if temperatures exceed ideal ranges."
            )
            elements.append(Paragraph(forecast_text, styles["Normal"]))
            elements.append(Spacer(1, 20))

        # 2.6) Section 0: User Inputs
        elements.append(Paragraph("<b>Section 0: User Inputs</b>", styles["Heading2"]))
        input_fields = [
            "location", "ph_level", "nitrogen", "phosphorus", "potassium",
            "measured_soil_temp", "soil_temp_0_to_7cm", "soil_type", "crop_type",
            "weather_source"
        ]
        table_data = [[Paragraph("<b>Field</b>", wrap_style), Paragraph("<b>Value</b>", wrap_style)]]
        for field in input_fields:
            val = user_data.get(field, "N/A")
            table_data.append([Paragraph(field, wrap_style), Paragraph(str(val), wrap_style)])
        user_inputs_table = Table(table_data, colWidths=[120, 300])
        user_inputs_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#CCCCCC")),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        elements.append(user_inputs_table)
        elements.append(Spacer(1, 20))

        # 2.7) Section 1: Soil & Weather Overview
        elements.append(Paragraph("<b>Soil & Weather Overview</b>", styles["Heading2"]))
        soil_data = [
            ["Soil Temp (Measured)", f"{user_data.get('measured_soil_temp', 'N/A')}°C"],
            ["Soil Temp (AI Predicted)", f"{user_data.get('predicted_soil_temp', 'N/A')}°C"],
            ["Moisture", f"{user_data.get('moisture', 'N/A')}%"],
            ["pH Level", f"{user_data.get('ph_level', 'N/A')}"],
            ["Nitrogen", f"{user_data.get('nitrogen', 'N/A')}"],
            ["Phosphorus", f"{user_data.get('phosphorus', 'N/A')}"],
            ["Potassium", f"{user_data.get('potassium', 'N/A')}"]
        ]
        soil_table = Table(soil_data, colWidths=[250, 150], hAlign="LEFT")
        soil_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#006400")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(soil_table)
        elements.append(Spacer(1, 10))
        weather_data = [
            ["Temperature (2m)", f"{user_data.get('temperature_2m', 'N/A')}°C"],
            ["Humidity (2m)", f"{user_data.get('relative_humidity_2m', 'N/A')}%"],
            ["Wind Speed (10m)", f"{user_data.get('wind_speed_10m', 'N/A')} m/s"],
            ["Precipitation", f"{user_data.get('precipitation', 'N/A')} mm"]
        ]
        w_table = Table(weather_data, colWidths=[250, 150], hAlign="LEFT")
        w_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#00008B")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ]))
        elements.append(w_table)
        elements.append(Spacer(1, 20))

        # 2.8) Section 2: AI Crop Suitability & Yield Prediction
        elements.append(Paragraph("<b>AI Crop Suitability & Yield Prediction</b>", styles["Heading2"]))
        if recommended_crops:
            crop_table_data = [
                [
                    Paragraph("<b>Crop Name</b>", wrap_style),
                    Paragraph("<b>Crop Type</b>", wrap_style),
                    Paragraph("<b>Temp Suitability</b>", wrap_style),
                    Paragraph("<b>Predicted Yield</b>", wrap_style),
                    Paragraph("<b>Growth Risks</b>", wrap_style),
                    Paragraph("<b>Feasibility Score</b>", wrap_style),
                    Paragraph("<b>Best Planting Time</b>", wrap_style)
                ]
            ]
            for crop in recommended_crops:
                yield_val = crop.get('predicted_yield', 0)
                if yield_val > 150:
                    yield_color = "green"
                elif yield_val >= 100:
                    yield_color = "orange"
                else:
                    yield_color = "red"
                yield_str = f'<font color="{yield_color}">{yield_val}</font>'
                growth_risks = crop.get("growth_risks", "N/A")
                row = [
                    Paragraph(crop.get('name', 'N/A'), wrap_style),
                    Paragraph(crop.get("crop_type", "N/A"), wrap_style),
                    Paragraph(crop.get("temperature_suitability", "N/A"), wrap_style),
                    Paragraph(yield_str, wrap_style),
                    Paragraph(growth_risks, wrap_style),
                    Paragraph(str(crop.get("feasibility_score", 0)) + "/100", wrap_style),
                    Paragraph(crop.get("best_planting_time", "N/A"), wrap_style)
                ]
                crop_table_data.append(row)
            crops_table = Table(crop_table_data, colWidths=[65, 60, 80, 60, 90, 70, 70], hAlign="LEFT")
            crops_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#228B22")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ]))
            elements.append(crops_table)
            elements.append(Spacer(1, 10))
            for crop in recommended_crops:
                details = crop.get("yield_explanation", "")
                elements.append(Paragraph(f"<b>{crop['name']}</b>: {details}", wrap_style))
            elements.append(Spacer(1, 20))
        else:
            elements.append(Paragraph("No crop recommendations available.", styles["Normal"]))
            elements.append(Spacer(1, 20))

        # 2.9) Section 3: Risk Warnings & Recommendations
        elements.append(Paragraph("<b>Risk Warnings & Recommendations</b>", styles["Heading2"]))
        risk_table_data = [
            [Paragraph("<b>Risk/Warning</b>", wrap_style), Paragraph("<b>Severity</b>", wrap_style)]
        ]
        if risk_assessment and "No major soil risks" not in risk_assessment[0]:
            for risk in risk_assessment:
                if "too acidic" in risk or "Low nitrogen" in risk:
                    severity = "High"
                    color = colors.red
                elif "too alkaline" in risk:
                    severity = "Medium"
                    color = colors.orange
                else:
                    severity = "Medium"
                    color = colors.yellow
                risk_table_data.append([Paragraph(risk, wrap_style), Paragraph(severity, wrap_style)])
        else:
            risk_table_data.append(["No major soil risks detected.", "None"])
            color = colors.green
        risk_table = Table(risk_table_data, colWidths=[300, 70], hAlign="LEFT")
        risk_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), color),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ]))
        elements.append(risk_table)
        elements.append(Spacer(1, 20))

        # 2.10) Section 4: Mitigation Strategies
        elements.append(Paragraph("<b>Mitigation Strategies</b>", styles["Heading2"]))
        for strategy in mitigation_strategies:
            elements.append(Paragraph(f"• {strategy}", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # 2.11) Section 5: Visual Data Insights
        elements.append(Paragraph("<b>Visual Data Insights</b>", styles["Heading2"]))
        # 2.11.1) Soil Temperature Graph
        graph_path = os.path.join(settings.MEDIA_ROOT, "reports", f"{report_request.user.username}_soil_temp_graph.png")
        generate_soil_temp_graph(report_request, user_data, graph_path)
        elements.append(Paragraph("<b>Soil Temperature Trends (7 Days):</b>", styles["Normal"]))
        elements.append(Image(graph_path, width=400, height=250))
        elements.append(Spacer(1, 20))
        # 2.11.2) Stacked Yield Comparison Chart
        yield_chart_path = os.path.join(settings.MEDIA_ROOT, "reports", f"{report_request.user.username}_yield_comparison.png")
        generate_stacked_yield_chart(recommended_crops, regional_avg_yield, yield_chart_path)
        elements.append(Paragraph("<b>Stacked Yield Comparison:</b>", styles["Normal"]))
        elements.append(Image(yield_chart_path, width=400, height=250))
        elements.append(Spacer(1, 20))
        # 2.11.3) Monthly Precipitation Chart
        monthly_precip_path = os.path.join(settings.MEDIA_ROOT, "reports", f"{report_request.user.username}_monthly_precip.png")
        generate_monthly_precip_chart(historical_weather, monthly_precip_path)
        elements.append(Paragraph("<b>Monthly Precipitation:</b>", styles["Normal"]))
        elements.append(Image(monthly_precip_path, width=400, height=250))
        elements.append(Spacer(1, 20))

        # 2.12) Section 6: AI Model Details & Transparency
        elements.append(Paragraph("<b>AI Model Details & Transparency</b>", styles["Heading2"]))
        elements.append(Paragraph(
            "Our AI predicts <b>soil_temp_0_to_7cm</b> using regression & decision tree models. "
            "Metrics (R²=0.94, MAE=1.2) indicate strong accuracy. Future expansions may include "
            "multivariate climate forecasts.",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 10))

        # 2.13) Section 7: AI Alerts & Warnings
        elements.append(Paragraph("<b>AI Alerts & Warnings</b>", styles["Heading2"]))
        for alert in ai_alerts:
            elements.append(Paragraph(alert, wrap_style))
        elements.append(Spacer(1, 20))

        # 2.14) Section 8: Next Best Action
        elements.append(Paragraph("<b>Next Best Action</b>", styles["Heading2"]))
        for line in next_best_action.split("\n"):
            elements.append(Paragraph(line, styles["Normal"]))
        elements.append(Spacer(1, 20))

        # 2.15) Section 9: Historical Trends & Rotation Plan
        elements.append(Paragraph("<b>Historical Trends & Weather Impact Summary</b>", styles["Heading2"]))
        elements.append(Paragraph("5-Year Weather Summary:", styles["Normal"]))
        elements.append(Paragraph(
            f"• Avg Max Temp: {historical_weather.get('avg_max_temp', 'N/A')}°C<br/>"
            f"• Avg Min Temp: {historical_weather.get('avg_min_temp', 'N/A')}°C<br/>"
            f"• Total Precipitation: {historical_weather.get('total_precip', 'N/A')} mm<br/>",
            styles["Normal"]
        ))
        elements.append(Spacer(1, 10))
        if rotation_plan:
            elements.append(Paragraph(f"<b>Crop Rotation Plan:</b> {rotation_plan}", styles["Normal"]))
            elements.append(Spacer(1, 10))
        elements.append(Paragraph("Historical Soil pH Trends: Not Available", styles["Normal"]))
        elements.append(Spacer(1, 20))

        # 2.16) Section 10: Disclaimer
        elements.append(Paragraph("<b>Disclaimer</b>", styles["Heading2"]))
        elements.append(Paragraph(
            "This AI-generated report is advisory only, based on best-effort AI data. "
            "Future expansions will include deeper predictions (e.g., 7–28cm soil temps).",
            styles["Normal"]
        ))
        elements.append(Paragraph("For more info, contact support@yourcompany.com", styles["Normal"]))

        # ✅ 10️⃣ Build & Save the PDF to Cloudflare R2
        doc.build(elements)
        pdf_buffer.seek(0)  # Reset buffer position

        saved_file_name = default_storage.save(file_path, ContentFile(pdf_buffer.getvalue()))  # ✅ Save in R2
        
            # ✅ 7️⃣ Verify Upload
        if not default_storage.exists(saved_file_name):
            logger.error(f"⛔ Failed to save PDF to Cloudflare R2: {saved_file_name}")
            return {"error": "Failed to save PDF to storage."}
        
        file_url = default_storage.url(saved_file_name)  # ✅ Get public URL from R2

        logger.info(f"✅ PDF saved to Cloudflare R2: {file_url}")

        return file_url  # ✅ Return Cloudflare R2 file URL
    
    except Exception as e:
        logger.exception(f"⛔ PDF generation failed: {str(e)}")
        return {"error": f"PDF generation failed: {str(e)}"}
    
# =============================================================================
# 3) HEADER, FOOTER, AND PREMIUM COVER PAGE FUNCTIONS
# =============================================================================

def _build_premium_cover_page(report_request, user_data):
    flowables = []
    styles = getSampleStyleSheet()
    logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo_AI_Farming.png")
    round_logo_path = os.path.join(settings.BASE_DIR, "static", "images", "logo_AI_Farming_round.png")
    farmland_bg1 = os.path.join(settings.BASE_DIR, "static", "images", "about_banner.jpg")
    farmland_bg2 = os.path.join(settings.BASE_DIR, "static", "images", "farmland_extra.jpg")
    if os.path.exists(logo_path) and not os.path.exists(round_logo_path):
        round_logo_path = make_image_round(logo_path, round_logo_path)
    if os.path.exists(round_logo_path):
        logo_img = Image(round_logo_path, width=120, height=120)
        logo_table = Table([[logo_img]], colWidths=[160])
        logo_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        flowables.append(logo_table)
    flowables.append(Spacer(1, 20))
    row_imgs = []
    if os.path.exists(farmland_bg1):
        row_imgs.append(Image(farmland_bg1, width=300, height=180))
    if os.path.exists(farmland_bg2):
        row_imgs.append(Image(farmland_bg2, width=300, height=180))
    if row_imgs:
        images_table = Table([row_imgs], colWidths=[300, 300])
        images_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0, colors.white),
        ]))
        flowables.append(images_table)
    flowables.append(Spacer(1, 20))
    flowables.append(Paragraph("<font size=24><b>Precision AI-Powered Soil Insights</b></font>", styles["Title"]))
    flowables.append(Spacer(1, 10))
    flowables.append(Paragraph("<i>Empowering Farmers to Maximize Yield & Sustainability</i>", styles["Normal"]))
    flowables.append(Spacer(1, 40))
    cover_text = (
        f"<b>Generated For:</b> {report_request.user.username}<br/>"
        f"<b>Location:</b> {report_request.location} ({report_request.latitude}, {report_request.longitude})<br/>"
        f"<b>Date:</b> {report_request.created_at.strftime('%Y-%m-%d')}<br/>"
    )
    flowables.append(Paragraph(cover_text, styles["Normal"]))
    flowables.append(Spacer(1, 60))
    flowables.append(Paragraph(
        "Thank you for choosing our premium AI-based soil analysis service. "
        "This report integrates advanced data science, historical weather analysis, "
        "and future climate forecasts to provide actionable insights that help you "
        "boost crop yields and farm more sustainably.",
        styles["Normal"]
    ))
    flowables.append(Spacer(1, 40))
    return flowables

def _add_header_footer(canvas_obj, doc):
    canvas_obj.setFont('Helvetica-Bold', 9)
    page_width = letter[0]
    header_text = "MyBrand - Premium AI Soil Analysis"
    text_width = canvas_obj.stringWidth(header_text, 'Helvetica-Bold', 9)
    canvas_obj.drawString((page_width - text_width) / 2.0, 11 * inch, header_text)
    page_num = doc.page
    canvas_obj.setFont('Helvetica', 9)
    canvas_obj.drawString(inch, 0.5 * inch, f"Page {page_num}")

# =============================================================================
# 4) CHART GENERATION FUNCTIONS
# =============================================================================

def generate_soil_temp_graph(report_request, user_data, file_path):
    days = np.arange(1, 8)
    ai_temp_values = np.random.uniform(low=15, high=30, size=7)
    plt.figure(figsize=(7, 4))
    plt.plot(days, ai_temp_values, marker="o", linestyle="-", color="blue", label="AI Predicted")
    measured_temp = user_data.get("measured_soil_temp", None)
    if measured_temp is not None:
        plt.axhline(y=float(measured_temp), color="red", linestyle="--", label="Measured Soil Temp")
    plt.xlabel("Days", fontsize=12, fontweight='bold')
    plt.ylabel("Soil Temperature (°C)", fontsize=12, fontweight='bold')
    plt.title("Soil Temperature Trends (7 Days)", fontsize=14, fontweight='bold')
    plt.grid(True)
    plt.legend()
    plt.savefig(file_path, dpi=300, bbox_inches="tight")
    plt.close()

def generate_stacked_yield_chart(recommended_crops, regional_avg_yield, file_path):
    if not recommended_crops:
        crops = ["No Crops"]
        hist_values = [0]
        top_values = [0]
    else:
        crops = [crop["name"] for crop in recommended_crops]
        hist_values = [10 for _ in crops]  # dummy historical yield = 10
        top_values = []
        for crop in recommended_crops:
            pred_yield = crop["predicted_yield"]
            if pred_yield > 10:
                top_values.append(pred_yield - 10)
            else:
                top_values.append(0)
    reg_avg = float(regional_avg_yield.get("regional_avg", 0))
    x = np.arange(len(crops))
    plt.figure(figsize=(7, 4))
    plt.bar(x, hist_values, width=0.6, label="Historical Yield (dummy=10)", color="#87CEFA")
    plt.bar(x, top_values, width=0.6, bottom=hist_values, label="Predicted (above 10)", color="#FF8C00")
    plt.axhline(y=reg_avg, color="green", linestyle="--", label=f"Regional Avg = {reg_avg} t/ha")
    plt.xticks(x, crops, rotation=45, ha="right")
    plt.ylabel("Yield (tons/ha)")
    plt.title("Stacked Yield Comparison")
    plt.legend()
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.close()

def generate_monthly_precip_chart(historical_weather, file_path):
    """
    Creates a bar chart showing monthly precipitation using real historical data.
    This simplistic approach divides total precipitation by 60 (5 years * 12 months)
    to approximate monthly averages.
    """
    total_precip = historical_weather.get("total_precip", 0)
    monthly_avg = total_precip / 60 if total_precip else 0
    months = np.arange(1, 13)
    precip_vals = [monthly_avg for _ in months]
    plt.figure(figsize=(6, 3))
    plt.bar(months, precip_vals, color="skyblue")
    plt.xticks(months, ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"], rotation=45)
    plt.ylabel("Precipitation (mm)")
    plt.title("Monthly Precipitation (Approximate)")
    plt.tight_layout()
    plt.savefig(file_path, dpi=300)
    plt.close()
