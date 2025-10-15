@echo off

setlocal
set "unixpath=%cd:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v init_hardware.py 2>&1 | tee init_hardware_out.txt"


timeout /t 3 >nul

endlocal