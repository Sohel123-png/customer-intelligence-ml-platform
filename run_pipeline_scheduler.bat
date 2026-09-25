@echo off

cd /d C:\Users\sasal\Downloads\churn_platform_django

call .venv\Scripts\activate.bat

python manage.py run_pipeline

echo.
echo Pipeline finished.