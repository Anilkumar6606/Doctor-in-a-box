# Doctor in a Box - Python Report Server Startup
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Doctor in a Box Report Server" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

Write-Host "Installing required Python packages..." -ForegroundColor Yellow
pip install -r requirements.txt

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "Starting Python Flask Server..." -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "Server will start on: http://localhost:5000" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Open your browser to: http://localhost:8000" -ForegroundColor White
Write-Host "2. (OR) Open index.html in your browser" -ForegroundColor White
Write-Host "3. Generate a report with screening details" -ForegroundColor White
Write-Host "4. Click PDF, Image, or WhatsApp buttons" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop the server" -ForegroundColor Red
Write-Host ""

python app.py
