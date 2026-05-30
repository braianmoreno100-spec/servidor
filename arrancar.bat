@echo off
cd C:\Users\braia\servidor

start "Servicios" cmd /k "python C:\Users\braia\servidor\servicios_programados.py"

call venv\Scripts\activate
venv\Scripts\python.exe -m uvicorn app.main:socket_app --host 0.0.0.0 --port 8000 --workers 1
pause