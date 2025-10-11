@echo off
echo Starting Team Registration System...
echo.
echo Database: Neon PostgreSQL
echo Server: http://localhost:5001
echo.
echo Opening browser...
start http://localhost:5001
echo.
echo Starting Flask application...
python app_minimal_working.py
pause