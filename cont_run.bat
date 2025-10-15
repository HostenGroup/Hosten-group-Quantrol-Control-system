@echo off

setlocal
set "unixpath=%cd:\=/%"
set "unixpath=/%unixpath::=%"

set "MSYSTEM=CLANG64"

:loop

call "C:\msys64\usr\bin\bash.exe" -lc "cd $unixpath% && artiq_run -v run_experiment.py 2>&1 | tee cont_run_out.txt"
set "ret=%ERRORLEVEL%"



::look for the specific failure
findstr /I /C:"WinError 10054" /C:"forcibly closed by the remote host" cont_run_out.txt >nul
if %ERRORLEVEL%==0 (
  echo [%date% %time%] WinError 10054 detected. Relaunching...
  echo [%date% %time%] WinError 10054 detected. Relaunching... >> cont_run_out.txt
  goto loop
)

echo [%date% %time%] Finished. Exit code %ret%. Not relaunching.
echo [%date% %time%] Finished. Exit code %ret%. Not relaunching. >> cont_run_out.txt

timeout /t 3 >nul

endlocal