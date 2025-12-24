@echo off
start "Python Service" cmd /k "cd /d ""C:\Users\gater\Desktop\study\USTC\IAT\GeoWeb\geoweb\apps\python-service"" && uvicorn python_service.app:app --reload"
start "Java Backend" cmd /k "cd /d ""C:\Users\gater\Desktop\study\USTC\IAT\GeoWeb\geoweb\apps\backend"" && mvn spring-boot:run"
start "Frontend Dev" cmd /k "cd /d ""C:\Users\gater\Desktop\study\USTC\IAT\GeoWeb\geoweb\apps\frontend"" && npm run dev"
