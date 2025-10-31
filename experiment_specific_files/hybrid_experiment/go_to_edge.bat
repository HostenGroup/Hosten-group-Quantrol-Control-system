@echo off

setlocal
set "unixpath=%~dp0"

set "unixpath=%unixpath:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v ../../ARTIQ_scripts/go_to_edge.py 2>&1 | tee ../../logs/go_to_edge_out.txt"


timeout /t 5 >nul

endlocal