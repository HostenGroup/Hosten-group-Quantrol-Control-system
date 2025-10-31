@echo off

setlocal
set "unixpath=%~dp0"

set "unixpath=%unixpath:\=/%"
set "unixpath=/%unixpath::=%"


set "MSYSTEM=CLANG64"


call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v ../../ARTIQ_scripts/run_experiment.py 2>&1 | tee ../../logs/run_experiment_out.txt"


timeout /t 5 >nul

endlocal