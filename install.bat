@echo off
set "DIR=%~dp0"
set "CLI_PATH=%DIR%core\interfaces\cli"

echo Adding OpenKatalog CLI to the User PATH...

:: Get current user path
for /f "tokens=2*" %%A in ('reg query HKCU\Environment /v PATH') do set "CURRENT_PATH=%%B"

:: Check if already in PATH
echo %CURRENT_PATH% | findstr /C:"%CLI_PATH%" >nul
if %errorlevel% equ 0 (
    echo OpenKatalog is already in your PATH.
) else (
    setx PATH "%CURRENT_PATH%;%CLI_PATH%"
    echo Successfully installed OpenKatalog globally!
    echo Please restart your Command Prompt to use the 'ok' command.
)
pause