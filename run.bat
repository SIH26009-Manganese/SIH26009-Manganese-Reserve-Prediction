@echo off
echo ============================================
echo  SIH 26009 - Manganese Exploration AI
echo  Starting Backend and Frontend...
echo ============================================
echo.

echo [1/2] Starting FastAPI Backend on port 8000...
start "Backend API" cmd /k "cd /d %~dp0 && python -m uvicorn backend.mock_api:app --reload --port 8000"

timeout /t 3 /nobreak >nul

echo [2/2] Starting Streamlit Dashboard on port 8501...
start "Streamlit Dashboard" cmd /k "cd /d %~dp0 && streamlit run app.py --server.port 8501"

echo.
echo ============================================
echo  Backend:  http://localhost:8000
echo  Dashboard: http://localhost:8501
echo  API Docs: http://localhost:8000/docs
echo ============================================
echo.
pause
