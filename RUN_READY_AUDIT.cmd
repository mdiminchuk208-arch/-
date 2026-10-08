@echo off
cd /d "%~dp0"
set "PYTHONPATH=src"
py -m unittest discover -s tests -v
if errorlevel 1 goto failed
py scripts/audit_ready_root_cause.py --report-root data/reports/ready_root_cause_local --workers 4
if errorlevel 1 goto failed
py scripts/summarize_ready_evidence.py data/reports/ready_root_cause_local
if errorlevel 1 goto failed
py scripts/render_ready_audit.py data/reports/ready_root_cause_local --report READY_AUDIT_LOCAL_REPORT.md
if errorlevel 1 goto failed
echo READY audit completed. See READY_AUDIT_LOCAL_REPORT.md
pause
exit /b 0
:failed
echo Stopped. Existing reports are preserved. Check the error above.
pause
exit /b 1
