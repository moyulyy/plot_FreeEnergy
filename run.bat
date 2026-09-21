@echo off
rem ============================================================
rem  Energy Profile Studio  -  Windows launcher
rem  Conda env : D:\miniconda3\envs\chem_env
rem ============================================================
setlocal
cd /d "%~dp0"

set "PY=D:\miniconda3\envs\chem_env\pythonw.exe"
set "SCRIPT=%~dp0Plot_EnergyProfile-Studio.py"

if not exist "%PY%" (
    echo [ERROR] Python interpreter not found:
    echo         %PY%
    echo Please check the conda environment path.
    pause
    exit /b 1
)

if not exist "%SCRIPT%" (
    echo [ERROR] Script not found:
    echo         %SCRIPT%
    pause
    exit /b 1
)

echo ============================================================
echo   Energy Profile Studio
echo   Python : %PY%
echo ============================================================
echo Starting, please wait...
echo.

"%PY%" "%SCRIPT%"

set "ERR=%ERRORLEVEL%"
if not "%ERR%"=="0" (
    echo.
    echo [ERROR] Program exited with code %ERR%.
    pause
)

endlocal
