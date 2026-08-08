Option Explicit

Dim shell, fileSystem, baseDir, exePath, scriptPath, launched
Set shell = CreateObject("WScript.Shell")
Set fileSystem = CreateObject("Scripting.FileSystemObject")

baseDir = fileSystem.GetParentFolderName(WScript.ScriptFullName)
exePath = baseDir & "\dist\WhiteFlood_BG_Remover.exe"
scriptPath = baseDir & "\whiteflood_app.py"
shell.CurrentDirectory = baseDir

If fileSystem.FileExists(exePath) Then
    shell.Run Quote(exePath), 0, False
    launched = True
Else
    launched = RunHidden("pythonw.exe " & Quote(scriptPath))
    If Not launched Then
        launched = RunHidden("pyw -3 " & Quote(scriptPath))
    End If
End If

If Not launched Then
    MsgBox "WhiteFlood belum bisa dijalankan." & vbCrLf & vbCrLf & _
           "Pastikan EXE sudah dibuat atau Python 3.11+ dan dependency sudah terpasang.", _
           vbExclamation, "WhiteFlood"
End If

Function Quote(value)
    Quote = Chr(34) & value & Chr(34)
End Function

Function RunHidden(command)
    On Error Resume Next
    Err.Clear
    shell.Run command, 0, False
    RunHidden = (Err.Number = 0)
    Err.Clear
    On Error GoTo 0
End Function
