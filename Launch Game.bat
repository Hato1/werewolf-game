@echo off
setlocal
title Beast of Temerev - Room Editor

cd /d "%~dp0"
if errorlevel 1 goto :failed

rem Do not modify the user's PATH; this script finds uv explicitly.
set "UV_NO_MODIFY_PATH=1"

call :find_uv
if defined UV_EXE goto :launch

echo Installing uv. This only happens once and may take a few minutes...
echo.
powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
if errorlevel 1 goto :failed

call :find_uv
if not defined UV_EXE goto :no_uv

:launch
echo Starting Game...
echo.
"%UV_EXE%" run run-game
if errorlevel 1 goto :failed
exit /b 0

:find_uv
set "UV_EXE="
where uv >nul 2>nul
if not errorlevel 1 set "UV_EXE=uv"
if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
if not defined UV_EXE if exist "%LOCALAPPDATA%\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\uv\uv.exe"
if not defined UV_EXE if exist "%LOCALAPPDATA%\uv\bin\uv.exe" set "UV_EXE=%LOCALAPPDATA%\uv\bin\uv.exe"
if not defined UV_EXE if exist "%LOCALAPPDATA%\Programs\uv\uv.exe" set "UV_EXE=%LOCALAPPDATA%\Programs\uv\uv.exe"
if not defined UV_EXE if exist "%USERPROFILE%\.cargo\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.cargo\bin\uv.exe"
exit /b 0

:no_uv
echo uv was installed but could not be found.
echo Tried PATH, %%USERPROFILE%%\.local\bin, %%LOCALAPPDATA%%\uv, and %%LOCALAPPDATA%%\Programs\uv.
goto :failed

:failed
echo.
echo The room editor could not be started.
echo Please send this window's contents to a developer.
pause
exit /b 1
