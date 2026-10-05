Write-Host "============================================" -ForegroundColor Cyan
Write-Host " SIH 26009 - Manganese Exploration AI" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/2] Starting FastAPI Backend on port 8000..." -ForegroundColor Yellow
$backend = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "backend.mock_api:app", "--reload", "--port", "8000" -PassThru -WorkingDirectory $PSScriptRoot

Start-Sleep -Seconds 3

Write-Host "[2/2] Starting Streamlit Dashboard on port 8501..." -ForegroundColor Yellow
$frontend = Start-Process -FilePath "streamlit" -ArgumentList "run", "app.py", "--server.port", "8501" -PassThru -WorkingDirectory $PSScriptRoot

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Backend:   http://localhost:8000" -ForegroundColor Green
Write-Host " Dashboard: http://localhost:8501" -ForegroundColor Green
Write-Host " API Docs:  http://localhost:8000/docs" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Press Ctrl+C to stop both services." -ForegroundColor DarkGray

$backend.WaitForExit()
$frontend.WaitForExit()
