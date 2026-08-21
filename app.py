"""
Doctor in a Box - Report Generation + PostgreSQL Screening API
Uses Flask + Pillow + SQLAlchemy
"""

from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import os
from datetime import datetime
import base64
from dotenv import load_dotenv

from database import db, init_db
from models import Screening, AppMeta

load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE_DIR, 'TEMPLETE .png')
OUTPUT_DIR = os.path.join(BASE_DIR, 'generated_reports')
os.makedirs(OUTPUT_DIR, exist_ok=True)

try:
    FONT_REGULAR = ImageFont.truetype("arialbd.ttf", 15)
    FONT_BOLD = ImageFont.truetype("arialbd.ttf", 18)
    FONT_SMALL = ImageFont.truetype("arialbd.ttf", 12)
except Exception:
    FONT_REGULAR = ImageFont.load_default()
    FONT_BOLD = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()

init_db(app)


def get_store_payload():
    rows = Screening.query.order_by(Screening.created_at.asc()).all()
    counter = AppMeta.get_value('counter', None)
    if counter is None:
        counter = len(rows) + 1
    else:
        try:
            counter = int(counter)
        except (TypeError, ValueError):
            counter = len(rows) + 1
    campaign = AppMeta.get_value('campaignLocation', '')
    if not isinstance(campaign, str):
        campaign = ''
    return {
        'history': [row.to_dict() for row in rows],
        'counter': counter,
        'campaignLocation': campaign,
    }


def next_screening_id():
    counter = AppMeta.get_value('counter', None)
    rows = Screening.query.count()
    try:
        counter = int(counter) if counter is not None else rows + 1
    except (TypeError, ValueError):
        counter = rows + 1

    while True:
        candidate = f"DIB-SCR-{str(counter).zfill(6)}"
        exists = Screening.query.filter_by(screening_id=candidate).first()
        if not exists:
            AppMeta.set_value('counter', counter + 1)
            return candidate
        counter += 1


@app.route('/api/health', methods=['GET'])
def health_check():
    try:
        db.session.execute(db.text('SELECT 1'))
        db_ok = True
    except Exception as exc:
        db_ok = False
        return jsonify({
            'status': 'degraded',
            'message': 'Report server is running but database is unavailable',
            'database': False,
            'error': str(exc),
        }), 503
    return jsonify({
        'status': 'ok',
        'message': 'Report server is running',
        'database': db_ok,
    })


@app.route('/api/store', methods=['GET'])
def get_store():
    """Return full store shape used by the frontend (history + counter + campaign)."""
    try:
        return jsonify({'success': True, **get_store_payload()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/store', methods=['PUT'])
def put_store():
    """Replace store (used for full sync / localStorage migration)."""
    try:
        data = request.json or {}
        history = data.get('history') or []
        if not isinstance(history, list):
            return jsonify({'success': False, 'error': 'history must be a list'}), 400

        incoming_ids = set()
        for item in history:
            if not isinstance(item, dict):
                continue
            sid = item.get('id') or item.get('screening_id')
            if not sid:
                continue
            incoming_ids.add(sid)
            existing = Screening.query.filter_by(screening_id=sid).first()
            if existing:
                Screening.from_payload(item, existing=existing)
            else:
                db.session.add(Screening.from_payload(item))

        # Remove screenings that are no longer in the client store
        if incoming_ids or history == []:
            stale = Screening.query.filter(~Screening.screening_id.in_(incoming_ids)).all() if incoming_ids else Screening.query.all()
            for row in stale:
                db.session.delete(row)

        if 'counter' in data:
            try:
                AppMeta.set_value('counter', int(data.get('counter') or 1))
            except (TypeError, ValueError):
                AppMeta.set_value('counter', len(history) + 1)
        if 'campaignLocation' in data:
            AppMeta.set_value('campaignLocation', data.get('campaignLocation') or '')

        db.session.commit()
        return jsonify({'success': True, **get_store_payload()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/screenings', methods=['GET'])
def list_screenings():
    try:
        rows = Screening.query.order_by(Screening.created_at.desc()).all()
        return jsonify({
            'success': True,
            'screenings': [row.to_dict() for row in rows],
            'count': len(rows),
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/screenings', methods=['POST'])
def create_screening():
    try:
        data = request.json or {}
        screening_id = data.get('id') or data.get('screening_id') or next_screening_id()
        existing = Screening.query.filter_by(screening_id=screening_id).first()
        if existing:
            return jsonify({'success': False, 'error': f'Screening {screening_id} already exists'}), 409

        data['id'] = screening_id
        row = Screening.from_payload(data)
        db.session.add(row)

        # Keep counter ahead of highest used id
        try:
            numeric = int(str(screening_id).split('-')[-1])
            current = AppMeta.get_value('counter', 1)
            current = int(current) if current is not None else 1
            if numeric >= current:
                AppMeta.set_value('counter', numeric + 1)
        except (TypeError, ValueError):
            pass

        if 'campaignLocation' in data:
            AppMeta.set_value('campaignLocation', data.get('campaignLocation') or '')

        db.session.commit()
        return jsonify({'success': True, 'screening': row.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/screenings/<screening_id>', methods=['GET'])
def get_screening(screening_id):
    row = Screening.query.filter_by(screening_id=screening_id).first()
    if not row:
        return jsonify({'success': False, 'error': 'Not found'}), 404
    return jsonify({'success': True, 'screening': row.to_dict()})


@app.route('/api/screenings/<screening_id>', methods=['PUT'])
def update_screening(screening_id):
    try:
        row = Screening.query.filter_by(screening_id=screening_id).first()
        if not row:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        data = request.json or {}
        data['id'] = screening_id
        Screening.from_payload(data, existing=row)
        db.session.commit()
        return jsonify({'success': True, 'screening': row.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/screenings/<screening_id>', methods=['DELETE'])
def delete_screening(screening_id):
    try:
        row = Screening.query.filter_by(screening_id=screening_id).first()
        if not row:
            return jsonify({'success': False, 'error': 'Not found'}), 404
        db.session.delete(row)
        db.session.commit()
        return jsonify({'success': True, 'deleted': screening_id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['GET'])
def get_settings():
    try:
        payload = get_store_payload()
        return jsonify({
            'success': True,
            'counter': payload['counter'],
            'campaignLocation': payload['campaignLocation'],
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    try:
        data = request.json or {}
        if 'counter' in data:
            AppMeta.set_value('counter', int(data.get('counter') or 1))
        if 'campaignLocation' in data:
            AppMeta.set_value('campaignLocation', data.get('campaignLocation') or '')
        db.session.commit()
        payload = get_store_payload()
        return jsonify({
            'success': True,
            'counter': payload['counter'],
            'campaignLocation': payload['campaignLocation'],
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/migrate-local', methods=['POST'])
def migrate_local():
    """Import browser localStorage dump into PostgreSQL (merge by screening id)."""
    try:
        data = request.json or {}
        history = data.get('history') or []
        imported = 0
        updated = 0
        for item in history:
            if not isinstance(item, dict):
                continue
            sid = item.get('id') or item.get('screening_id')
            if not sid:
                continue
            existing = Screening.query.filter_by(screening_id=sid).first()
            if existing:
                Screening.from_payload(item, existing=existing)
                updated += 1
            else:
                db.session.add(Screening.from_payload(item))
                imported += 1

        if 'counter' in data:
            try:
                AppMeta.set_value('counter', int(data.get('counter') or 1))
            except (TypeError, ValueError):
                pass
        if data.get('campaignLocation'):
            AppMeta.set_value('campaignLocation', data.get('campaignLocation') or '')

        db.session.commit()
        return jsonify({
            'success': True,
            'imported': imported,
            'updated': updated,
            **get_store_payload(),
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/', methods=['GET'])
def home_page():
    return send_from_directory(BASE_DIR, 'index.html')


@app.route('/dashboard', methods=['GET'])
def dashboard_page():
    return send_from_directory(BASE_DIR, 'dashboard.html')


@app.route('/records', methods=['GET'])
def records_page():
    return send_from_directory(BASE_DIR, 'records.html')


@app.route('/api/generate-image', methods=['POST'])
def generate_image():
    try:
        data = request.json
        person = data.get('person', {})
        tests = data.get('tests', [])
        report_id = data.get('reportId', 'DIB-SCR-000000')

        if not os.path.exists(TEMPLATE_PATH):
            return jsonify({'error': f'Template not found: {TEMPLATE_PATH}'}), 400

        template = Image.open(TEMPLATE_PATH).convert('RGB')
        render_scale = 3
        img = template.resize((template.width * render_scale, template.height * render_scale), Image.Resampling.LANCZOS)
        draw = ImageDraw.Draw(img)

        text_color = (11, 43, 74)
        sx = img.width / 1024
        sy = img.height / 1536

        def font(size, bold=False):
            try:
                return ImageFont.truetype("arialbd.ttf" if bold else "arial.ttf", max(1, int(size * sy)))
            except Exception:
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

        img_byte_arr = BytesIO()
        img.save(img_byte_arr, format='PNG', quality=95)
        img_byte_arr.seek(0)
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

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
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            return jsonify({'error': 'Invalid filename'}), 400

        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'Report not found'}), 404

        return send_file(file_path, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/add-watermark', methods=['POST'])
def add_watermark():
    try:
        data = request.json
        img_base64 = data.get('imageData', '').split(',')[-1]
        watermark_text = data.get('watermarkText', 'CONFIDENTIAL')

        img_data = base64.b64decode(img_base64)
        img = Image.open(BytesIO(img_data))
        draw = ImageDraw.Draw(img)

        try:
            font = ImageFont.truetype("arial.ttf", 60)
        except Exception:
            font = ImageFont.load_default()

        gray_img = Image.new('RGBA', img.size, (255, 255, 255, 0))
        gray_draw = ImageDraw.Draw(gray_img)
        gray_draw.text((img.width // 4, img.height // 2), watermark_text,
                       fill=(200, 200, 200, 128), font=font)

        img = Image.alpha_composite(img.convert('RGBA'), gray_img).convert('RGB')

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
    try:
        file_path = os.path.join(OUTPUT_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404

        return send_file(file_path, as_attachment=True, mimetype='image/png')
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/<path:filename>', methods=['GET'])
def project_file(filename):
    allowed_extensions = ('.html', '.png', '.jpg', '.jpeg', '.json', '.js', '.css')
    safe_name = os.path.basename(filename)
    file_path = os.path.join(BASE_DIR, safe_name)
    if safe_name.lower().endswith(allowed_extensions) and os.path.exists(file_path):
        return send_from_directory(BASE_DIR, safe_name)
    return jsonify({'error': 'File not found'}), 404


if __name__ == '__main__':
    print("Doctor in a Box Report Server + PostgreSQL")
    print("Running on http://localhost:5000")
    print("API:")
    print("  GET/PUT  /api/store")
    print("  GET/POST /api/screenings")
    print("  GET/PUT/DELETE /api/screenings/<id>")
    print("  POST /api/migrate-local")
    print("  GET  /api/health")
    app.run(debug=True, host='localhost', port=5000)
