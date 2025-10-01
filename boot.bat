@echo off
echo Set WshShell = CreateObject("WScript.Shell") > %temp%\temp.vbs
echo WshShell.Run ".\pythonw.exe copyer.pyw", 0 >> %temp%\temp.vbs
echo Set WshShell = Nothing >> %temp%\temp.vbs
wscript %temp%\temp.vbs
del %temp%\temp.vbs
