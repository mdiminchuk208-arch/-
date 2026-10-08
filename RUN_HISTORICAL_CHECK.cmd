@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=src"
py -m unittest discover -s tests -v
if errorlevel 1 goto failed
py scripts/run_historical_portfolio.py --days 180 --workers 4 --mode BACKTEST --report-root data/reports/local_portfolio_180
if errorlevel 1 goto failed
py scripts/run_historical_portfolio.py --days 180 --workers 4 --mode SHADOW --report-root data/reports/local_portfolio_shadow
if errorlevel 1 goto failed
echo.
echo Offline reports: data/reports/local_portfolio_180 and data/reports/local_portfolio_shadow
pause
exit /b 0
:failed
echo.
echo Check failed. Read the error above. No exchange orders are sent by this script.
pause
exit /b 1
