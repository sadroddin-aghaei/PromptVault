@echo off
REM Prompt Vault - Windows build (run from the project folder)
setlocal
if not exist .venv ( py -3.12 -m venv .venv || goto :err )
call .venv\Scripts\activate.bat || goto :err
python -m pip install --upgrade pip || goto :err
pip install -r requirements.txt || goto :err
python -m pytest -q || goto :err
if /I "%1"=="onefile" ( set PV_ONEFILE=1 ) else ( set PV_ONEFILE=0 )
pyinstaller --noconfirm --clean PromptVault.spec || goto :err
echo.
if "%PV_ONEFILE%"=="1" ( echo Done: dist\PromptVault.exe ) else ( echo Done: dist\PromptVault\PromptVault.exe )
exit /b 0
:err
echo Build failed.
exit /b 1
