@echo off
REM Pembungkus untuk Windows Task Scheduler.
REM Jalankan file ini sebagai Program di Task Scheduler.
cd /d "%~dp0"
pythonw.exe logbook_dermaga.py
