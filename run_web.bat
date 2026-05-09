@echo off
title Udemy Dashboard Startup
echo Starting...

:: Di chuyen vao thu muc chua file nay
cd /d "%~dp0"

:: Di chuyen vao thu muc Web
cd Web

:: Chay Streamlit
streamlit run Web.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start. Make sure streamlit is installed.
    pause
)

pause
