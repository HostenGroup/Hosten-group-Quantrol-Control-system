@echo OFF			::makes the system NOT open a visible terminal window

set "winpath=%cd%"		::gets the path of the bat.file
set "unixpath=%winpath:\=/%"	::converts the path to unix format
set "unixpath=/%unixpath::=%"	::converts the path to unix format

set "MSYSTEM=CLANG64"		::sets to use CLANG64

"C:\msys64\msys2_shell.cmd" -c "cd %unixpath% && artiq_run -v init_hardware.py 2>&1 | tee init_hardware_out.txt" 
 
::launches the .py file andputh the printed output to the .txt file