@echo off
REM Quick activation script for Windows CMD
REM Usage: activate.bat

if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    echo Virtual environment activated
    echo Python: %VIRTUAL_ENV%\Scripts\python.exe
) else (
    echo Virtual environment not found. Run setup_venv.ps1 first.
    exit /b 1
)

