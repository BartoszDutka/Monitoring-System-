@echo off
echo Setting up GTK environment for WeasyPrint...

:: Try to locate GTK installation
set GTK_PATH=C:\Program Files\GTK3-Runtime Win64
if not exist "%GTK_PATH%" set GTK_PATH=C:\Program Files (x86)\GTK3-Runtime Win64

:: If GTK is installed, set environment variables
if exist "%GTK_PATH%" (
    echo Found GTK installation at %GTK_PATH%
    set PATH=%PATH%;%GTK_PATH%\bin
    set GTK_BASEPATH=%GTK_PATH%
    set GTK_EXE_PREFIX=%GTK_PATH%
    echo GTK environment variables set successfully.
) else (
    echo GTK installation not found.
    echo Please install GTK3 Runtime from:
    echo https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
    pause
    exit /b 1
)

:: Run the Python application with correct environment
echo Running application with GTK support...
python "%~dp0app.py" %*

:: If you need to run a specific script, just change app.py above to the script you want to run