# 🏥 Doctor in a Box - Report Generation System

Professional health screening report generator with browser-based image/PDF export.

## 🌐 Netlify Deployment

This project is ready for Netlify as a static site.

### Deploy Settings
```
Build command: leave empty
Publish directory: .
```

### Files Prepared for Netlify
- `netlify.toml` sets the static publish folder.
- `.netlifyignore` keeps local Python/cache/generated report files out of deploys.
- `index.html` is the deployed app entry point.

### Deploy Options
1. Drag this project folder into Netlify Drop.
2. Or push the folder to GitHub and import the repo in Netlify.

The Flask `app.py` server is only for local/backend experimentation and is not required for the current deployed app.

## 🚀 Quick Start

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Start the Python Server
Choose ONE method:

**Option A: Double-click (Windows)**
```
Double-click: start_server.bat
```

**Option B: Command Line (Windows)**
```bash
python app.py
```

**Option C: PowerShell (Windows)**
```powershell
powershell -ExecutionPolicy Bypass -File start_server.ps1
```

**Option D: Any OS (Terminal)**
```bash
cd "c:\Users\anilk\Downloads\DIB\screening test"
python app.py
```

You should see:
```
🚀 Doctor in a Box Report Server
📍 Running on http://localhost:5000
```

### Step 3: Open the Application

**Option A: Live Server (Recommended)**
```bash
python -m http.server 8000
# Then open: http://localhost:8000
```

**Option B: Direct File Access**
- Double-click `index.html` in Explorer
- OR drag `index.html` into your browser

### Step 4: Generate Reports

1. Fill in patient screening details
2. Select tests (Blood Pressure, Blood Sugar, etc.)
3. Enter test results
4. Click **"Generate Report"**
5. Use action buttons:
   - 📥 **PDF** - Download as PDF
   - 🖼️ **Image** - Download as PNG
   - 💬 **WhatsApp** - Share via WhatsApp

---

## 🔧 Python Backend Features

### API Endpoints

#### 1. Generate Image from Template
```
POST /api/generate-image
Content-Type: application/json

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
    {
      "label": "Blood Pressure",
      "value": "120/49",
      "unit": "mmHg"
    }
  ],
  "reportId": "DIB-SCR-000001"
}

Response:
{
  "success": true,
  "dataUrl": "data:image/png;base64,...",
  "filename": "report_DIB-SCR-000001_20260813_103000.png"
}
```

#### 2. Compress Image
```
POST /api/compress-image
Content-Type: application/json

{
  "imageData": "data:image/png;base64,...",
  "quality": 85
}

Response:
{
  "success": true,
  "dataUrl": "data:image/png;base64,...",
  "originalSize": "2.5 MB",
  "compressedSize": "1.2 MB",
  "savedPercentage": "52%"
}
```

#### 3. Add Watermark
```
POST /api/add-watermark
Content-Type: application/json

{
  "imageData": "data:image/png;base64,...",
  "watermarkText": "CONFIDENTIAL"
}

Response:
{
  "success": true,
  "dataUrl": "data:image/png;base64,..."
}
```

#### 4. Health Check
```
GET /api/health

Response:
{
  "status": "ok",
  "message": "Report server is running"
}
```

---

## 📁 Project Structure

```
screening test/
├── index.html                 # Main application
├── app.py                    # Python Flask backend
├── requirements.txt          # Python dependencies
├── start_server.bat          # Windows batch startup
├── start_server.ps1          # PowerShell startup
├── report template .png      # Template image
├── visys-cloud .png          # Logo
├── doctor in a box .jpeg     # Logo
├── report-template.json      # Data template
└── generated_reports/        # Auto-created, stores reports
```

---

## ✨ Features

### Image Generation
- ✅ Professional template-based reports
- ✅ Dynamic data overlay
- ✅ High-quality PNG output
- ✅ Automatic date/time stamping

### Image Processing
- ✅ Compression with quality control
- ✅ Watermark addition
- ✅ Base64 encoding for web sharing

### Export Formats
- 📄 PDF (via html2pdf.js + canvas)
- 🖼️ PNG (via Python Pillow)
- 💬 WhatsApp (image + auto-download)

### Report Sharing
- ✅ Direct download
- ✅ WhatsApp Web API integration
- ✅ Auto-delete temp files
- ✅ Batch processing support

---

## 🐍 Python Dependencies

```
Flask==2.3.3          # Web server
Pillow==10.0.0        # Image processing
python-dotenv==1.0.0  # Environment variables
```

**Install all at once:**
```bash
pip install -r requirements.txt
```

---

## 🔧 Troubleshooting

### Issue: "Python server not running"
**Solution:** Start the server first
```bash
python app.py
```
Make sure you see: `Running on http://localhost:5000`

### Issue: "Could not load template image"
**Solution:** Check if `report template .png` exists in the same folder as `index.html`

### Issue: "Font errors" when generating images
**Solution:** Update font paths in `app.py`
```python
FONT_REGULAR = ImageFont.truetype("C:\\Windows\\Fonts\\arial.ttf", 16)
```

### Issue: Port 5000 already in use
**Solution:** Edit `app.py` and change the port:
```python
app.run(host='localhost', port=5001)  # Use 5001 instead
```

### Issue: "CORS errors" in browser console
**Solution:** Use the HTTP server instead of file:// protocol
```bash
python -m http.server 8000
# Then open http://localhost:8000
```

---

## 🎯 Next Steps

### Want to Enhance Reports?
1. **Add Chart/Graphs** - Use matplotlib in Python
2. **Digital Signature** - Add doctor signature image
3. **Batch Reports** - Process multiple reports at once
4. **Email Delivery** - Send via SMTP
5. **Cloud Storage** - Save to AWS S3/Google Drive

### Want to Deploy?
1. Deploy Flask to Heroku/PythonAnywhere
2. Upload HTML to GitHub Pages
3. Use Vercel for static hosting
4. Docker containerization available

### Want to Customize?
1. Modify template image in Photoshop/GIMP
2. Adjust text positions in `app.py`
3. Add new fields to report
4. Change colors/fonts

---

## 📱 Mobile Support

The app works on mobile browsers, but:
- WhatsApp sharing is more reliable on mobile
- PDF generation may be slower
- Responsive design auto-adjusts for all screens

---

## 🔒 Security Notes

- ✅ No patient data is stored on server (unless you save it)
- ✅ All processing happens locally
- ✅ Use HTTPS in production
- ✅ Add authentication before deployment
- ✅ Sanitize all inputs

---

## 📞 Support

For issues or questions, check:
1. Browser console (F12) for errors
2. Terminal output for server logs
3. Check if all files exist in the folder
4. Try the HTTP server method instead of file://

---

## 📝 License

© 2026 Doctor in a Box. All rights reserved.

---

**Happy reporting! 🎉**
