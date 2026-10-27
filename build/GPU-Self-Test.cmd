@echo off
cd /d "%~dp0"
start /wait "" "%~dp0GSRIM.exe" --self-test "%~dp0gpu-self-test.json"
if exist "%~dp0gpu-self-test.json" (
  type "%~dp0gpu-self-test.json"
) else (
  echo Self-test report missing. Check results\startup-error.txt.
)
pause
