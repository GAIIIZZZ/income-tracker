' Income Tracker - silent launcher
'
' Double-click this file (or a shortcut to it) to start the app with no
' visible terminal windows at all - just the browser opening on its own.
' Meant for friends who already ran setup.bat once and don't want to deal
' with command prompts.
'
' Before starting the servers, it runs "git pull" to fetch the latest code
' from GitHub automatically, so you don't have to manually re-download the
' project to get updates. If git isn't installed, or there's no internet,
' this step is skipped and the app starts with whatever code is already
' on disk.
'
' Since there are no visible windows, all output is written to log files
' instead: update_log.txt (project root), backend_log.txt (backend/),
' frontend_log.txt (frontend/). Check those if something doesn't work.

Set fso = CreateObject("Scripting.FileSystemObject")
Set WshShell = CreateObject("WScript.Shell")
strPath = fso.GetParentFolderName(WScript.ScriptFullName)

If Not fso.FolderExists(strPath & "\backend\.venv") Or Not fso.FolderExists(strPath & "\frontend\node_modules") Then
    WshShell.Popup "Setup hasn't been run yet on this computer." & vbCrLf & vbCrLf & _
        "Please double-click setup.bat first (only needed once), then try this again.", _
        0, "Income Tracker", 48
    WScript.Quit
End If

' Auto-update from GitHub (skipped silently if git/internet isn't available)
WshShell.CurrentDirectory = strPath
WshShell.Run "cmd /c git pull > update_log.txt 2>&1", 0, True

' Start backend, hidden
WshShell.CurrentDirectory = strPath & "\backend"
WshShell.Run "cmd /c call .venv\Scripts\activate.bat && set PYTHONIOENCODING=utf-8 && uvicorn app.main:app --host 127.0.0.1 --port 8000 > backend_log.txt 2>&1", 0, False

WScript.Sleep 4000

' Start frontend, hidden
WshShell.CurrentDirectory = strPath & "\frontend"
WshShell.Run "cmd /c node server.js > frontend_log.txt 2>&1", 0, False

WScript.Sleep 2000

' Open the app in the default browser
WshShell.Run "http://localhost:3000"
