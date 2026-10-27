@echo off
setlocal
pushd "%~dp0"
py -3.14 -c "import sys; assert sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
    echo Python 3.14 x64 is required. Trying the Python installation manager...
    py install --yes 3.14
)
py -3.14 -c "import sys; assert sys.maxsize > 2**32" >nul 2>&1
if errorlevel 1 (
    echo Install Python 3.14 x64 from https://www.python.org/downloads/
    popd
    exit /b 1
)
py -3.14 bootstrap.py %*
set "airCanvasResult=%errorlevel%"
popd
exit /b %airCanvasResult%

