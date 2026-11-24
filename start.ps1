# Jarvis Local Prototype Launcher
Write-Host "Starting Jarvis Backend (FastAPI on http://127.0.0.1:8000)..." -ForegroundColor Cyan
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\backend'; & '.\.venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

Start-Sleep -Seconds 2

Write-Host "Starting Jarvis Frontend (Next.js on http://localhost:3000)..." -ForegroundColor Green
Start-Process -FilePath "powershell.exe" -ArgumentList "-NoExit", "-Command", "cd '$PSScriptRoot\frontend'; npm.cmd run dev"

Write-Host "Jarvis Prototype is launching! Open http://localhost:3000 in your browser." -ForegroundColor Yellow
