@echo off

setlocal
set "unixpath=%~dp0"
for %%I in ("%unixpath%\..\..") do set "unixpath=%%~fI"
set "unixpath=%unixpath:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v ../../ARTIQ_scripts/set_slow_dds_states.py 2>&1 | tee ../../logs/set_slow_dds_states_out.txt"


timeout /t 5 >nul

endlocal