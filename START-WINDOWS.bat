@echo off
cd /d "%~dp0"
echo.
echo        CLAUDE MISSION CONTROL
 echo       Local read-only observer
 echo.
where py >nul 2>nul
if %errorlevel%==0 (py -3 server.py) else (python server.py)
pause
