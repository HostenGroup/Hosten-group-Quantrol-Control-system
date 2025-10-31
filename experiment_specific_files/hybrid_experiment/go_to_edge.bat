@echo off

setlocal
set "unixpath=%cd:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v go_to_edge.py 2>&1 | tee go_to_edge_out.txt"


timeout /t 3 >nul

endlocal