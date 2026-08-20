@echo off
title Doctor in a Box - Python Report Server
color 0A

echo.
echo ========================================
echo   Doctor in a Box Report Server
echo ========================================
echo.
echo Installing required Python packages...
echo.

REM Install requirements
pip install -r requirements.txt

echo.
echo ========================================
echo Starting Python Flask Server...
echo ========================================
echo.
echo Server will start on: http://localhost:5000
echo.
echo Next Steps:
echo 1. Open your browser to: http://localhost:8000
echo 2. (OR) Open index.html in your browser
echo 3. Generate a report with screening details
echo 4. Click PDF, Image, or WhatsApp buttons
echo.
echo Press Ctrl+C to stop the server
echo.

REM Start Flask app
python app.py

pause
