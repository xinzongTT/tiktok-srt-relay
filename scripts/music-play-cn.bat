@echo off
REM music-play-cn.bat
REM China side: pull music stream from VPS and play locally (Windows)
REM Usage: music-play-cn.bat

setlocal enabledelayedexpansion

set RED=[91m
set GREEN=[92m
set YELLOW=[93m
set CYAN=[96m
set NC=[0m

if not exist "..\.env" (
    echo %RED%[ERROR] .env not found. Copy from VPS project directory.%NC%
    exit /b 1
)

for /f "usebackq tokens=1,2 delims==" %%a in ("..\.env") do (
    set "%%a=%%b"
)

if "%PUBLIC_HOST%"=="" (
    echo %RED%[ERROR] PUBLIC_HOST not set in .env%NC%
    exit /b 1
)

set SRT_URL=srt://%PUBLIC_HOST%:%SRT_PORT%?streamid=read:%MUSIC_PATH%^&latency=%MUSIC_LATENCY%^&passphrase=%MUSIC_READ_PASSPHRASE%^&pbkeylen=16

where ffplay >nul 2>&1
if %errorlevel% equ 0 (
    set PLAYER=ffplay
    set ARGS=-i "%SRT_URL%" -nodisp
    goto :play
)

where vlc >nul 2>&1
if %errorlevel% equ 0 (
    set PLAYER=vlc
    set ARGS=-I dummy --play-and-exit "%SRT_URL%"
    goto :play
)

where mpv >nul 2>&1
if %errorlevel% equ 0 (
    set PLAYER=mpv
    set ARGS=--no-video "%SRT_URL%"
    goto :play
)

echo %RED%[ERROR] No supported player found. Install ffplay, vlc, or mpv.%NC%
exit /b 1

:play
echo %CYAN%========================================%NC%
echo %CYAN%  Music Player - VPS -^> China%NC%
echo %CYAN%========================================%NC%
echo VPS    : %PUBLIC_HOST%:%SRT_PORT%
echo Path   : read:%MUSIC_PATH%
echo Latency: %MUSIC_LATENCY% us
echo Player : %PLAYER%
echo.
echo %YELLOW%Press Ctrl+C to stop.%NC%
echo.

%PLAYER% %ARGS%
