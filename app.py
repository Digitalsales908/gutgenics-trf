 # Standard Libraries
import os
import io
import base64
from datetime import datetime

# Third-party Libraries
import requests
import boto3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

# ReportLab (PDF generation)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader, simpleSplit
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle, Image
from flask import Flask, request, jsonify, send_file
import pandas as pd
import io
import uuid  # 
from reportlab.platypus import Paragraph, Frame
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY

from reportlab.lib.utils import ImageReader


# Optional PDF styling/HTML rendering library

app = Flask(__name__)
CORS(app)


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Read from environment variables
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")

# Power Automate Endpoint
POWER_AUTOMATE_URL = "https://prod-17.centralindia.logic.azure.com:443/workflows/67e56ac6dcfe471cb9b0f6cba927b564/triggers/manual/paths/invoke?api-version=2016-06-01&sp=%2Ftriggers%2Fmanual%2Frun&sv=1.0&sig=W0j-bfkxxRGuWY1HxMCvlv1zenty1Z98Pahjjjehprs"  # Replace with your actual flow URL

# # Initialize S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY
)

submitted_forms = []  # Global list to hold all form submissions


from dotenv import load_dotenv
load_dotenv()
from datetime import datetime

def extract_form_data(req):
    """Extracts and returns full form data including checkboxes and radios."""

    # Generate ID like: DG20250718143030
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")  # Note the lowercase 'y' for 2-digit year
    unique_id = f"DG{timestamp}"
    return {
        "id": unique_id,

        # Basic Details
        "full_name": req.form.get("full_name"),
        "email": req.form.get("email"),
        "dob": req.form.get("dob"),
        "gender": req.form.get("gender"),
        "contact": req.form.get("contact"),
        "address": req.form.get("address"),
        "native_place": req.form.get("native_place"),
        "mother_tongue": req.form.get("mother_tongue"),
        "height": req.form.get("height"),
        "weight": req.form.get("weight"),
        "sampling_date": req.form.get("sampling_date"),
        "sampling_time": req.form.get("sampling_time"),
        "reason": req.form.getlist("reason"),
        "reason_other": req.form.get("reason_other"),

        # Signature
        "signature_data": req.form.get("signature_data"),

        # Checkboxes (multi-value)
        "test_requested": req.form.getlist("test_requested"),
        "sample_type": req.form.getlist("sample_type"),
        "diet": req.form.getlist("diet"),
        "exercise": req.form.getlist("exercise"),
        "ethnicity": req.form.getlist("ethnicity"),

        # Conditional fields
        "medications": req.form.get("medications"),
        "medication_details": req.form.get("medication_details"),
        "disease": req.form.get("disease"),
        "disease_details": req.form.get("disease_details"),

        "tobacco": req.form.get("tobacco"),
        "cigarettes_per_week": req.form.get("cigarettes_per_week"),

        "alcohol": req.form.get("alcohol"),
        "alcohol_days_per_week": req.form.get("alcohol_days_per_week"),
        "alcohol_quantity": req.form.get("alcohol_quantity"),
        "ethnicity_other": req.form.get("ethnicity_other"),
        "consent_given": req.form.get("consent_given") == "true",
    }


def decode_signature(signature_data):
    """Decodes base64 image data to ImageReader object."""
    if not signature_data:
        return None
    header, encoded = signature_data.split(",", 1)
    signature_bytes = base64.b64decode(encoded)
    return ImageReader(io.BytesIO(signature_bytes))


def generate_pdf(data, signature_image):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 30 * mm
    box_margin = 20 * mm
    line_height = 6 * mm
    field_length = 60 * mm
    checkbox_size = 4 * mm
    section_gap = 10 * mm

    # LEFT_LOGO_PATH = "F:/progenics_code_automation/TRF_Consent_Form/static/Images/gutgenics_logo.png"
    # RIGHT_LOGO_PATH = "F:/progenics_code_automation/TRF_Consent_Form/static/Images/progenics_logo.jpg"
    # BACKGROUND_IMAGE_PATH = "F:/progenics_code_automation/TRF_Consent_Form/static/Images/progenics_logo.jpg"
    
    LEFT_LOGO_PATH = os.path.join(BASE_DIR, "static", "Images", "gutgenics_logo.png")
    RIGHT_LOGO_PATH = os.path.join(BASE_DIR, "static", "Images", "progenics_logo.jpg")
    BACKGROUND_IMAGE_PATH = os.path.join(BASE_DIR, "static", "Images", "progenics_logo.jpg")

    LOGO_WIDTH = 50 * mm
    LOGO_HEIGHT = 20 * mm
    LOGO_Y = height - 30 * mm
    LEFT_LOGO_X = 20 * mm
    RIGHT_LOGO_X = width - LOGO_WIDTH - 20 * mm

    def add_watermark(canvas):
        canvas.saveState()
        canvas.setFillAlpha(0.1)
        watermark_width = 100 * mm
        watermark_height = 100 * mm
        x = (width - watermark_width) / 2
        y = (height - watermark_height) / 2
        canvas.drawImage(BACKGROUND_IMAGE_PATH, x, y, width=watermark_width, height=watermark_height,
                         preserveAspectRatio=True, mask='auto')
        canvas.setFillAlpha(1)
        canvas.restoreState()

    def add_logo(canvas):
        canvas.drawImage(LEFT_LOGO_PATH, LEFT_LOGO_X, LOGO_Y, width=LOGO_WIDTH, height=LOGO_HEIGHT,
                         preserveAspectRatio=True, mask='auto')
        canvas.drawImage(RIGHT_LOGO_PATH, RIGHT_LOGO_X, LOGO_Y, width=LOGO_WIDTH, height=LOGO_HEIGHT,
                         preserveAspectRatio=True, mask='auto')

    def draw_header():
        nonlocal y
        c.setFont("Helvetica-Bold", 16)
        c.setFillColor(colors.black)
        c.drawCentredString(width / 2, y, "Gutgenics TRF")
        c.setStrokeColor(colors.black)
        c.line(box_margin, y - 5, width - box_margin, y - 5)
        y -= 10 * mm  # Reduced from 25mm to 10mm

    def draw_justified_paragraph(text, font_name, font_size, line_width, start_x, start_y):
        nonlocal y
        lines = simpleSplit(text, font_name, font_size, line_width)
        for line in lines:
            words = line.split()
            if len(words) == 1 or line == lines[-1]:  # last line or single word line: left-align
                c.drawString(start_x, y, line)
            else:
                total_word_width = sum(c.stringWidth(w, font_name, font_size) for w in words)
                space_width = (line_width - total_word_width) / (len(words) - 1)
                x = start_x
                for word in words:
                    c.drawString(x, y, word)
                    x += c.stringWidth(word, font_name, font_size) + space_width
            y -= line_height
        y -= line_height / 2  # space between paragraphs
    
    START_Y = height - 30 * mm  # Reduced top margin

    y = START_Y  # At the beginning
    def new_page():
        nonlocal y
        c.showPage()
        add_watermark(c)
        add_logo(c)
        y = START_Y  # use consistent reduced top margin

    
    def draw_field(label, value="", underline=True):
        nonlocal y
        if y < 50:
            new_page()

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)

        # Draw label
        c.drawString(box_margin, y, label)

        # Calculate starting point for value
        text_x = box_margin + c.stringWidth(label, "Helvetica", 10) + 10
        max_width = width - text_x - box_margin

        # Wrap the value text
        wrapped_lines = simpleSplit(str(value), "Helvetica", 10, max_width)
        line_count = len(wrapped_lines)

        # Draw dashed line ABOVE the text (before printing value)
        if underline:
            c.setDash(2, 2)
            c.line(text_x, y-1, text_x + 60 * mm, y-1)
            c.setDash([])

        # Draw each line of the value
        for i, line in enumerate(wrapped_lines):
            c.drawString(text_x, y, line)
            if i < line_count - 1:
                y -= line_height
                if y < 50:
                    new_page()
        y -= line_height

    def draw_checkbox_group(label, options, selected_values=None, columns=2):
        nonlocal y
        if selected_values is None:
            selected_values = []
        rows_needed = (len(options) + columns - 1) // columns
        if y - (rows_needed * line_height + line_height) < 40:
            new_page()
        c.setFont("Helvetica", 10)
        c.drawString(box_margin, y, label)
        y -= line_height
        col_width = (width - 2 * box_margin) / columns
        text_offset = checkbox_size + 3 * mm
        for i, option in enumerate(options):
            col = i % columns
            row = i // columns
            x = box_margin + col * col_width
            current_y = y - row * line_height
            checkbox_y = current_y - 2 * mm
            c.rect(x, checkbox_y, checkbox_size, checkbox_size, fill=0)
            if option in selected_values:
                c.setFont("Helvetica-Bold", 12)
                c.drawString(x + 1, checkbox_y + 1, "✓")
                c.setFont("Helvetica", 10)
            text = option
            max_text_width = col_width - text_offset - 5 * mm
            while c.stringWidth(text, "Helvetica", 10) > max_text_width and len(text) > 3:
                text = text[:-4] + "..."
            c.drawString(x + text_offset, current_y - 3, text)
        y -= (rows_needed * line_height) + (section_gap / 2)

    # Begin first page
    add_watermark(c)
    add_logo(c)
    draw_header()

    # --- Populate Data ---
    draw_field("Full Name:", data.get("full_name", ""))
    draw_field("Gender:", data.get("gender", ""))
    draw_field("Date of Birth:", data.get("dob", ""))
    draw_field("Height:", data.get("height", ""))
    draw_field("Weight:", data.get("weight", ""))
    draw_field("Email:", data.get("email", ""))
    draw_field("Contact:", data.get("contact", ""))
    draw_field("Address:", data.get("address", ""))
    draw_checkbox_group("Test Requested:", ["Standard", "Prime", "Elite"], data.get("test_requested", []), columns=3)
    draw_checkbox_group("Sample Type:", ["Stool", "Biopsy", "Others"], data.get("sample_type", []), columns=3)
    draw_field("Sampling Date:", data.get("sampling_date", ""))
    draw_field("Sampling Time:", data.get("sampling_time", ""))
    draw_checkbox_group("What is the Primary reason for ordering this test:", ["IBD", "IBS", "Constipation", "Bloating", "GERD", "Other"],
                        data.get("reason", []), columns=3)
    if "Other" in data.get("reason", []):
        draw_field("Other reason:", data.get("reason_other", ""))
    draw_checkbox_group("Are you using any medications?", ["Yes", "No"],
                        ["Yes"] if data.get("medications", "").lower() == "yes" else ["No"])
    if data.get("medications", "").lower() == "yes":
        draw_field("If yes, specify:", data.get("medication_details", ""),underline=False)

    draw_checkbox_group("Have you been diagnosed with any disease so far?", ["Yes", "No"],
                        ["Yes"] if str(data.get("disease", "")).lower() == "yes" else ["No"])
    if data.get("disease", "").lower() == "yes":
        draw_field("If yes, specify:", data.get("disease_details", ""), underline=False)

    draw_checkbox_group("Which of the following do you eat?", ["Veg", "Non-Veg"], data.get("diet", []))
    draw_checkbox_group("Exercise:", ["Sedentary", "Mild", "Vigorous"],
                        data.get("exercise", []), columns=3)
    draw_checkbox_group("Tobacco/Nicotine:", ["Yes", "No"],
                        ["Yes"] if data.get("tobacco", "").lower() == "yes" else ["No"])
    if data.get("tobacco", "").lower() == "yes":
        draw_field("If yes, no. of cigarettes/week:", data.get("cigarettes_per_week", ""))
    new_page()
    alcohol_status = data.get("alcohol", "").lower()
    alcohol_selected = ["Yes"] if alcohol_status == "yes" else ["No"] if alcohol_status == "no" else ["Occasionally"]
    draw_checkbox_group("Alcohol:", ["Yes", "No", "Occasionally"], alcohol_selected, columns=3)
    if alcohol_status in ["yes", "occasionally"]:
        draw_field("No. of days in a week:", data.get("alcohol_days_per_week", ""))
        draw_field("Quantity (ml/week):", data.get("alcohol_quantity", ""))
    ethnicity_val = data.get("ethnicity", ["No"]) or ["No"]
    draw_checkbox_group(
        "Nationality/Ethnicity:",
        ["Asian Indian (Indian, Pakistan, Bangladesh, Sri Lanka, Nepal)"],
        ["Asian Indian (Indian, Pakistan, Bangladesh, Sri Lanka, Nepal)"] if ethnicity_val[0].lower() == "yes" else []
    )
    if ethnicity_val[0].lower() != "yes":
        draw_field("If not Asian Indian, please specify:", data.get("ethnicity_other", ""))

    draw_field("Native Place:", data.get("native_place", ""))
    draw_field("Mother Tongue:", data.get("mother_tongue", ""))
    # Consent Section
    c.setFont("Helvetica-Bold", 12)
    c.drawString(box_margin, y, "Informed Consent for Gut Health Testing")
    y -= line_height

    consent_texts = [
        "I Voluntarily consent to submit my sample(s) for gut health testing. I understand that the sample I provided will be analyzed to provide insights into known diseases, traits, drug responses, etc., I recognize that the results will primarily indicate my risk or predisposition for specific diseases, traits, or responses to medications.",
        "The test results are not intended for diagnostic purposes; rather they serve as predictive screening for preventive healthcare. I have been informed about the clinical significance and implications of the tests, the services offered, the methodologies employed, and their limitationsI have had the chance to ask questions before signing this document, and I have been assured that any inquiries regarding the tests will be addressed by the progenics support team and staff.",
        "The specimen, clinical information, and data in a de-identified manner may be used for research, educational studies, and/or publication when appropriate. Rest assured, your name and any personal identifying details will not be associated with the results of any studies or publications. For customers who consent to this, their samples may be reused, retested, and reanalyzed to create data for research and /or to develop new products.",
        "For more information, please visit www.progenicslabs.com"
    ]
    c.setFont("Helvetica", 10)
    max_width = width - 2 * box_margin  # available width for wrapping

    for text in consent_texts:
        needed_height = (len(simpleSplit(text, "Helvetica", 10, max_width)) + 1) * line_height
        if y < needed_height + 20:
            new_page()
        draw_justified_paragraph(text, "Helvetica", 10, max_width, box_margin, y)


    draw_checkbox_group("Providing Consent for Gut Health Testing:", ["Yes", "No"],
                        ["No"] if data.get("consent_given") else ["Yes"])
    if signature_image:
        draw_field("Signature:", underline=True)
        image_reader = ImageReader(signature_image)
        c.drawImage(image_reader, box_margin + 60, y + 10, width=200, height=30, mask="auto")
    else:
        draw_field("Signature:", data.get("signature", ""))
    draw_field("Place:", data.get("native_place", ""))
    draw_field("Date:", data.get("signature_date", datetime.now().strftime("%d/%m/%Y")))
    c.save()
    buffer.seek(0)
    return buffer

def upload_pdf_to_s3(pdf_buffer, full_name):
    """Uploads the PDF buffer to S3 and returns the file key."""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    key = f"Consent_Forms/{full_name.replace(' ', '_')}_{timestamp}.pdf"
    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=key,
        Body=pdf_buffer.getvalue(),
        ContentType='application/pdf'
    )
    return key

def send_email_via_power_automate(email, full_name, pdf_bytes):
    """Base64 encodes PDF and sends it to Power Automate flow."""
    encoded_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    payload = {
        "email": email,
        "subject": "Your TRF Consent Form",
        "body": f"Dear {full_name}, please find your submitted consent form attached.",
        "filename": "Consent_Form.pdf",
        "filecontent": encoded_pdf
    }
    response = requests.post(POWER_AUTOMATE_URL, json=payload)
    return response.status_code, response.text


@app.route('/')
def index():
    return render_template('form.html')

# @app.route("/submit", methods=["POST"])
# def submit():
#     try:
#         form_data = extract_form_data(request)
#         print("✔️ Received Form Data:", form_data)

#         signature_data = form_data.get("signature_data")
#         if not signature_data:
#             raise ValueError("Missing signature_data in form submission.")

#         signature_image = decode_signature(signature_data)
#         print("✔️ Signature Decoded.")

#         pdf_buffer = generate_pdf(form_data, signature_image)
#         print("✔️ PDF Generated.")

#         # Store the form data (excluding signature image for privacy)
#         submitted_forms.append({k: v for k, v in form_data.items() if k != "signature_data"})

#         # Email sending disabled
#         # status_code, response_text = send_email_via_power_automate(
#         #     form_data["email"], form_data["full_name"], pdf_buffer
#         # )
#         # print(f"✔️ Email sent | Status: {status_code} | Response: {response_text}")

#         return jsonify({
#             "message": "Form submitted successfully. (Email sending disabled)",
#             # "email_status": status_code,
#             # "email_response": response_text,
#             "form_id": form_data["id"]
#         })

#     except Exception as e:
#         print("❌ Internal Server Error:", str(e))
#         return jsonify({"error": str(e)}), 500

import os
import base64
import pandas as pd
from PIL import Image
from io import BytesIO
from flask import request, jsonify, send_file
from datetime import datetime

SIGNATURES_DIR = "signatures"
os.makedirs(SIGNATURES_DIR, exist_ok=True)

import boto3
import uuid

AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
BUCKET_NAME = os.environ.get("BUCKET_NAME", "trf-consent-form-data")
FOLDER = "signatures"  # Optional S3 subfolder

s3 = boto3.client(
    "s3",
    region_name=AWS_REGION,
    aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY")
)

EXCEL_S3_KEY = "excel/form_data.xlsx"
LOCAL_EXCEL_PATH = "form_data.xlsx"

try:
    s3.download_file(BUCKET_NAME, EXCEL_S3_KEY, LOCAL_EXCEL_PATH)
    print("✔️ Restored Excel file from S3.")
except Exception as e:
    print(f"ℹ️ No Excel backup found in S3: {e}")

def upload_to_s3(local_path, filename):
    s3_key = f"{FOLDER}/{filename}"

    s3.upload_file(
        Filename=local_path,
        Bucket=BUCKET_NAME,
        Key=s3_key,
        ExtraArgs={"ContentType": "image/png"}  # Removed ACL
    )

    return f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"


def decode_signature(data_url):
    header, encoded = data_url.split(",", 1)
    data = base64.b64decode(encoded)
    return Image.open(BytesIO(data))


@app.route("/submit", methods=["POST"])
def submit_form():
    form_data = extract_form_data(request)

    # Decode and save signature
    signature_data = form_data.get("signature_data")
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    if signature_data:
        try:
            signature_image = decode_signature(signature_data)
            form_data["signature_path"] = f"signature_{form_data['id']}_{timestamp}.png"
            print("✔️ Signature Decoded.")
        except Exception as e:
            return jsonify({"error": f"Signature decoding failed: {str(e)}"}), 400
    else:
        signature_image = None
        form_data["signature_path"] = None

    # Remove raw base64 before saving form
    form_data.pop("signature_data", None)

    # ✅ Generate the PDF
    pdf_buffer = generate_pdf(form_data, signature_image)
    pdf_bytes = pdf_buffer.getvalue()  # 🔁 Read it once and reuse as bytes
    pdf_filename = f"TRF_{form_data['id']}_{timestamp}.pdf"
    print("✔️ PDF Generated.")

    # ✅ Upload to S3
    try:
        s3.upload_fileobj(
            io.BytesIO(pdf_bytes),  # Re-wrap in BytesIO
            BUCKET_NAME,
            f"pdfs/{pdf_filename}",
            ExtraArgs={"ContentType": "application/pdf"}
        )
        print(f"✔️ Uploaded PDF to S3 as pdfs/{pdf_filename}")
    except Exception as e:
        print(f"❌ Failed to upload PDF to S3: {e}")
        return jsonify({"error": "PDF upload failed"}), 500

    # ✅ Send Email via Power Automate
    # email = form_data.get("email")
    # full_name = form_data.get("full_name") or f"{form_data.get('first_name', '')} {form_data.get('last_name', '')}"
    # try:
    #     status_code, response_text = send_email_via_power_automate(email, full_name, pdf_bytes)
    #     if status_code in [200, 202]:
    #         print("📧 Email accepted for processing.")
    #     else:
    #         print(f"❌ Email sending failed with status {status_code}: {response_text}")
    # except Exception as e:
    #     print(f"❌ Email sending exception: {e}")
    # ✅ Save data to Excel

    new_df = pd.DataFrame([form_data])
    for col in new_df.columns:
        new_df[col] = new_df[col].apply(lambda x: ", ".join(x) if isinstance(x, list) else x)

    file_path = "form_data.xlsx"
    if os.path.exists(file_path):
        existing_df = pd.read_excel(file_path)
        updated_df = pd.concat([existing_df, new_df], ignore_index=True)
    else:
        updated_df = new_df

    updated_df.to_excel(file_path, index=False)
    try:
        s3.upload_file(
            Filename=file_path,
            Bucket=BUCKET_NAME,
            Key="excel/form_data.xlsx",
            ExtraArgs={"ContentType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        )
        print("✔️ Uploaded Excel to S3.")
    except Exception as e:
        print(f"❌ Failed to upload Excel to S3: {e}")

    return jsonify({
        "message": "Form submitted, PDF uploaded, and email sent.",
        "pdf_url": f"https://{BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/pdfs/{pdf_filename}"
    })

@app.route("/download_excel", methods=["GET"])
def download_excel():
    file_path = "form_data.xlsx"

    if not os.path.exists(file_path):
        return jsonify({"message": "No submissions yet."}), 400

    return send_file(
        file_path,
        download_name="form_submissions.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

if __name__ == "__main__":
    app.run(debug=True)



