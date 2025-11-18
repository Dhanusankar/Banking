@echo off
echo Installing requirements and starting AI orchestrator...
"%~dp0\..\..\..\AppData\Local\Programs\Python\Python313\python.exe" -m pip install -r requirements.txt
"%~dp0\..\..\..\AppData\Local\Programs\Python\Python313\python.exe" -m uvicorn server:app --reload --port 8000
