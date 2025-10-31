@echo off

setlocal
set "unixpath=%cd:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v set_slow_dds_states.py 2>&1 | tee set_slow_dds_states_out.txt"


timeout /t 3 >nul

endlocal