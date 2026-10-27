@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    call setup.bat
    if errorlevel 1 (
        echo Setup did not complete. Read README_FA.md for help.
        pause
        popd
        exit /b 1
    )
)
".venv\Scripts\python.exe" run.py %*
set "airCanvasResult=%errorlevel%"
if not "%airCanvasResult%"=="0" pause
popd
exit /b %airCanvasResult%

