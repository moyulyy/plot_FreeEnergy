@echo off
rem ============================================================
rem  重新生成图标并打包单文件免安装 exe
rem  Conda env : D:\miniconda3\envs\chem_env
rem  输出      : dist\EnergyProfileStudio.exe
rem ============================================================
setlocal
cd /d "%~dp0"

set "PY=D:\miniconda3\envs\chem_env\python.exe"

if not exist "%PY%" (
    echo [ERROR] Python not found: %PY%
    pause
    exit /b 1
)

echo [1/3] 生成图标 app.ico / app.png ...
"%PY%" make_icon.py || goto :error

echo [2/3] 清理旧构建 ...
if exist build rmdir /s /q build
if exist dist  rmdir /s /q dist

echo [3/3] PyInstaller 打包中（可能需要几分钟）...
"%PY%" -m PyInstaller --noconfirm --clean EnergyProfileStudio.spec || goto :error

echo.
echo ============================================================
echo  完成！输出文件： dist\EnergyProfileStudio.exe
echo ============================================================
pause
endlocal
exit /b 0

:error
echo.
echo [ERROR] 打包失败，请查看上方日志。
pause
endlocal
exit /b 1
