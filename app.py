"""
Doctor in a Box - Report Generation Server
Uses Flask + Pillow + ReportLab for professional image/PDF generation
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import json
import os
from datetime import datetime
import base64

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Configuration (absolute paths for Render / Gunicorn)
TEMPLATE_PATH = os.path.join(BASE_DIR, 'TEMPLETE .png')
OUTPUT_DIR = os.path.join(BASE_DIR, 'generated_reports')

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Font paths (adjust based on your system)
try:
    FONT_REGULAR = ImageFont.truetype("arialbd.ttf", 15)
    FONT_BOLD = ImageFont.truetype("arialbd.ttf", 18)
    FONT_SMALL = ImageFont.truetype("arialbd.ttf", 12)
except:
    # Fallback to default font
    FONT_REGULAR = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()


@app.route('/api/health', methods=['GET'])
def health_check():
    """Check if server is running"""
    return jsonify({'status': 'ok', 'message': 'Report server is running'})


@app.route('/', methods=['GET'])
def home_page():
    """Serve the screening app"""
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    """Serve the analytics dashboard"""
    return send_from_directory(BASE_DIR, 'dashboard.html')


@app.route('/records', methods=['GET'])
def records_page():
    """Serve the master records page"""
    return send_from_directory(BASE_DIR, 'records.html')


@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    """
    Generate report image from template
    Expected JSON:
    {
        "person": {
            "name": "John Doe",
            "contact": "9876543210",
            "email": "john@example.com",
            "location": "Hyderabad",
            "camp": "Camp ABC",
            "date": "2026-08-13",
            "time": "10:30 AM"
        },
        "tests": [
            {"label": "Blood Pressure", "value": "120/49", "unit": "mmHg"},
            ...
        ],
        "reportId": "DIB-SCR-000001"
    }
    """
    try:
        data = request.json
        person = data.get('person', {})
        tests = data.get('tests', [])
        report_id = data.get('reportId', 'DIB-SCR-000000')

        # Load template image
        if not os.path.exists(TEMPLATE_PATH):
            return jsonify({'error': f'Template not found: {TEMPLATE_PATH}'}), 400

        template = Image.open(TEMPLATE_PATH).convert('RGB')
        render_scale = 3
        img = template.resize((template.width * render_scale, template.height * render_scale), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)

        # Color for text
        text_color = (11, 43, 74)  # #0b2b4a

        sx = img.width / 1024
        sy = img.height / 1536

        def font(size, bold=False):
            try:
                return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", max(1, int(size * sy)))
            except:
                return ImageFont.load_default()

        def pos(x, y):
            return (int(x * sx), int(y * sy))

        def fit_text(x, y, text, font=FONT_REGULAR, max_width=220, anchor='lm', color=text_color):
            original = '—' if text is None else str(text)
            value = original
            width = int(max_width * sx)
            while len(value) > 1 and draw.textlength(value, font=font) > width:
                value = value[:-1]
            if value != original:
                while len(value) > 1 and draw.textlength(f'{value}...', font=font) > width:
                    value = value[:-1]
                value = f'{value}...'
            draw.text(pos(x, y), value, fill=color, font=font, anchor=anchor)

        def rect(x1, y1, x2, y2, fill, outline=None, width=2):
            draw.rounded_rectangle(
                (int(x1 * sx), int(y1 * sy), int(x2 * sx), int(y2 * sy)),
                radius=int(8 * sx),
                fill=fill,
                outline=outline,
                width=max(1, int(width * sx))
            )

        def section_title(title, x, y, w):
            rect(x, y, x + w, y + 40, fill=(233, 246, 245), outline=(184, 220, 216))
            fit_text(x + 16, y + 21, title, FONT_BOLD, w - 32, color=(0, 117, 111))

        def money(value):
            if value in (None, '', '—'):
                return 'Rs. 0/-'
            if isinstance(value, (int, float)):
                return f'Rs. {value}/-'
            raw = str(value).replace('₹', 'Rs. ')
            return raw if '/-' in raw else f'{raw}/-'

        gender_age = ' / '.join(part for part in [
            person.get('gender', '').strip() if isinstance(person.get('gender'), str) else person.get('gender'),
            f"{person.get('age')} yrs" if person.get('age') else ''
        ] if part) or '—'
        report_label = data.get('reportName') or data.get('reports') or f"{len(tests)} Test(s)"

        teal = (0, 117, 111)
        line_color = (200, 221, 229)

        fit_text(512, 215, 'HEALTH SCREENING REPORT', font(30, True), 760, anchor='mm', color=teal)

        card_y = 260
        card_h = 190
        rect(48, card_y, 496, card_y + card_h, fill=(255, 255, 255), outline=line_color)
        rect(528, card_y, 976, card_y + card_h, fill=(255, 255, 255), outline=line_color)
        fit_text(72, card_y + 30, 'Patient Details', font(18, True), 360, color=teal)
        fit_text(552, card_y + 30, 'Report Details', font(18, True), 360, color=teal)

        def draw_info_line(x, y, label, value, label_width=110, value_width=280):
            fit_text(x, y, label, font(15, True), label_width)
            fit_text(x + label_width + 8, y, ':', font(15, True), 12)
            fit_text(x + label_width + 28, y, value or '—', font(15), value_width)

        draw_info_line(72, card_y + 68, 'Name', person.get('name') or 'Unknown', 90, 300)
        draw_info_line(72, card_y + 102, 'Gender/Age', gender_age, 90, 300)
        draw_info_line(72, card_y + 136, 'Mobile', person.get('contact') or '—', 90, 300)
        draw_info_line(72, card_y + 170, 'Email', person.get('email') or '—', 90, 300)

        draw_info_line(552, card_y + 68, 'Patient ID', report_id, 112, 270)
        draw_info_line(552, card_y + 102, 'Date', person.get('date') or '—', 112, 270)
        draw_info_line(552, card_y + 136, 'Time', person.get('time') or '—', 112, 270)
        draw_info_line(552, card_y + 170, 'Reports', report_label, 112, 270)

        address_text = person.get('location') or person.get('address') or person.get('camp') or ''
        if address_text:
            fit_text(72, 482, f'Address: {address_text}', font(15, True), 820)

        rect(48, 520, 976, 572, fill=(11, 111, 104), outline=(11, 111, 104))
        fit_text(512, 547, 'TEST RESULTS', font(24, True), 760, anchor='mm', color=(255, 255, 255))

        table_x = 48
        table_y = 610
        table_w = 928
        header_h = 34
        row_h = 44
        rows = []
        for test in tests[:10]:
            if isinstance(test, str):
                label = test.split('|')[0] or test
                rows.append({'label': label, 'value': '—', 'unit': '—', 'reference': '—', 'price': 0})
            elif isinstance(test, dict):
                rows.append(test)
        if not rows:
            rows = [{'label': 'No checkups selected', 'value': '—', 'unit': '—', 'reference': '—', 'price': 0}]
        rect(table_x, table_y, table_x + table_w, table_y + header_h + (len(rows) * row_h) + 58, fill=(255, 255, 255), outline=line_color)
        draw.rectangle((int(table_x * sx), int(table_y * sy), int((table_x + table_w) * sx), int((table_y + header_h) * sy)), fill=(234, 246, 245))

        columns = [
            ('Test Name', table_x + 18, 248),
            ('Result', table_x + 286, 196),
            ('Unit', table_x + 500, 88),
            ('Reference Range', table_x + 612, 212),
            ('Price', table_x + 844, 66),
        ]
        for label, x, width in columns:
            fit_text(x, table_y + 18, label, font(15, True), width, color=teal)

        computed_total = 0
        for index, test in enumerate(rows):
            y = table_y + header_h + (index * row_h)
            if index % 2 == 0:
                draw.rectangle((int(table_x * sx), int(y * sy), int((table_x + table_w) * sx), int((y + row_h) * sy)), fill=(247, 251, 252))
            price = test.get('price', 0) if isinstance(test, dict) else 0
            if isinstance(price, (int, float)):
                computed_total += price
            fit_text(table_x + 18, y + 22, test.get('label') or test.get('name') or 'Test', font(14), 248)
            fit_text(table_x + 286, y + 22, test.get('value', '—'), font(14), 196)
            fit_text(table_x + 500, y + 22, test.get('unit') or '—', font(14), 88)
            fit_text(table_x + 612, y + 22, test.get('reference') or 'As per range', font(14), 212)
            fit_text(table_x + 844, y + 22, money(price).replace('Rs. ', ''), font(14), 66)

        rendered_total = data.get('amount', data.get('totalAmount', computed_total))
        total_y = table_y + header_h + (len(rows) * row_h) + 32
        fit_text(table_x + 18, total_y, 'Total Amount', font(17, True), 220)
        fit_text(table_x + 844, total_y, money(rendered_total).replace('Rs. ', ''), font(17, True), 66)

        # Convert to base64
        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        # Also save to file
        filename = f"{OUTPUT_DIR}/report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        img.save(filename)

        return jsonify({
            'success': True,
            'dataUrl': f'data:image/png;base64,{img_base64}',
            'filename': os.path.basename(filename)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload-report', methods=['POST'])
def upload_report():
    """Save a report image and return a shareable URL for WhatsApp."""
    try:
        data = request.json or {}
        img_base64 = data.get('imageData', '').split(',')[-1]
        report_id = data.get('reportId', 'report')
        safe_id = ''.join(c for c in str(report_id) if c.isalnum() or c in '-_') or 'report'
        filename = f"share_{safe_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        file_path = os.path.join(OUTPUT_DIR, filename)

        img_data = base64.b64decode(img_base64)
        with open(file_path, 'wb') as f:
            f.write(img_data)

        share_url = request.host_url.rstrip('/') + f'/api/reports/{filename}'
        return jsonify({
            'success': True,
            'shareUrl': share_url,
            'filename': filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports/<filename>', methods=['GET'])
def serve_shared_report(filename):
    """Serve a shared report image."""
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        return send_file(file_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def compress_image():
    """
    Compress image
    Expected: base64 image data + quality (1-95)
    """
    try:
        data = request.json
        img_base64 = data.get('imageData', '').split(',')[-1]
        quality = data.get('quality', 85)

        # Decode base64
        img_data = base64.b64decode(img_base64)
        img = Image.open(BytesIO(img_data))

        # Compress
        output = BytesIO()
        img.save(output, format='PNG', quality=quality, optimize=True)
        output.seek(0)

        compressed_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
        original_size = len(img_base64) / 1024  # KB
        compressed_size = len(compressed_base64) / 1024  # KB

        return jsonify({
            'success': True,
            'dataUrl': f'data:image/png;base64,{compressed_base64}',
            'originalSize': f'{original_size:.2f} KB',
            'compressedSize': f'{compressed_size:.2f} KB',
            'savedPercentage': f'{((original_size - compressed_size) / original_size * 100):.1f}%'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/add-watermark', methods=['POST'])
def add_watermark():
    """
    Add watermark text to image
    Expected: base64 image + watermark text
    """
    try:
        data = request.json
        img_base64 = data.get('imageData', '').split(',')[-1]
        watermark_text = data.get('watermarkText', 'CONFIDENTIAL')

        # Decode base64
        img_data = base64.b64decode(img_base64)
        img = Image.open(BytesIO(img_data))
        draw = ImageDraw.Draw(img)

        # Add watermark
        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except:
            font = ImageFont.load_default()

        # Semi-transparent watermark
        gray_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
        gray_draw = ImageDraw.Draw(gray_img)
        gray_draw.text((img.width // 4, img.height // 2), watermark_text, 
                       fill=(200, 200, 200, 128), font=font)
        
        img = Image.alpha_composite(img.convert('RGBA'), gray_img).convert('RGB')

        # Convert back to base64
        output = BytesIO()
        img.save(output, format='PNG')
        output.seek(0)
        watermarked_base64 = base64.b64encode(output.getvalue()).decode('utf-8')

        return jsonify({
            'success': True,
            'dataUrl': f'data:image/png;base64,{watermarked_base64}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Download generated report"""
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(file_path, as_attachment=True, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/<path:filename>', methods=['GET'])
def project_file(filename):
    """Serve local HTML/image assets used by the static pages"""
    allowed_extensions = ('.html', '.png', '.jpg', '.jpeg', '.json', '.js', '.css')
    safe_name = os.path.basename(filename)
    file_path = os.path.join(BASE_DIR, safe_name)
    if safe_name.lower().endswith(allowed_extensions) and os.path.exists(file_path):
        return send_from_directory(BASE_DIR, safe_name)
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    print("🚀 Doctor in a Box Report Server")
    print("📍 Running on http://localhost:5000")
    print("✅ API endpoints:")
    print("   POST /api/generate-image  - Generate report from template")
    print("   POST /api/upload-report   - Upload report for WhatsApp sharing")
    print("   GET  /api/reports/<file>  - View shared report image")
    print("   POST /api/compress-image  - Compress/optimize image")
    print("   POST /api/add-watermark   - Add watermark to image")
    print("   GET  /api/health          - Health check")
    print("   GET  /dashboard           - Dashboard page")
    print("   GET  /records             - Master records page")
    print("\n💡 Open your HTML app and use the Image/PDF buttons")
    
    app.run(debug=True, host='localhost', port=5000)
