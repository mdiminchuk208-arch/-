@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=src"
py -m unittest discover -s tests -v
set "test_result=%ERRORLEVEL%"
echo.
echo Test exit code: %test_result%
pause
exit /b %test_result%
