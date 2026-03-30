; Inno Setup script for PapaRaZ
; Install Inno Setup from: https://jrsoftware.org/isinfo.php
; Build: right-click this file → Compile, or: iscc paparaz_setup.iss

#define AppName      "PapaRaZ"
#define AppVersion   "0.8.0"
#define AppPublisher "Alejandro Lichtenfeld"
#define AppURL       "https://github.com/lichtenfeld/paparaz"
#define AppExeName   "PapaRaZ.exe"
#define AppIcon      "..\assets\paparaz.ico"
#define ExeSource    "..\dist\PapaRaZ.exe"

[Setup]
AppId={{E2F4A1B3-7C6D-4E5F-8A9B-0D1E2F3A4B5C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist
OutputBaseFilename=PapaRaZ_Setup_{#AppVersion}
SetupIconFile={#AppIcon}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
; Require Windows 10 or later
MinVersion=10.0

; Uninstall previous version automatically
CloseApplications=yes
CloseApplicationsFilter={#AppExeName}
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";   Description: "{cm:CreateDesktopIcon}";   GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startupentry";  Description: "Start {#AppName} automatically at Windows login"; GroupDescription: "Startup:"; Flags: unchecked

[Files]
Source: "{#ExeSource}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}";              Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}";   Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";        Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Auto-start on login (mirrors the in-app setting)
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
  ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExeName}"""; \
  Flags: uninsdeletevalue; Tasks: startupentry

[Run]
Filename: "{app}\{#AppExeName}"; \
  Description: "{cm:LaunchProgram,{#StringChange(AppName, '&', '&&')}}"; \
  Flags: nowait postinstall skipifsilent

[UninstallRun]
; Remove from startup registry on uninstall
Filename: "reg"; Parameters: "delete ""HKCU\Software\Microsoft\Windows\CurrentVersion\Run"" /v ""{#AppName}"" /f"; \
  Flags: runhidden; RunOnceId: "RemoveStartup"

[Code]
{ Abort installer if the exe hasn't been built yet }
function InitializeSetup(): Boolean;
begin
  if not FileExists(ExpandConstant('{src}\..\dist\{#AppExeName}')) then
  begin
    MsgBox(
      'PapaRaZ.exe not found in dist\.' + #13#10 +
      'Please run build.bat first to create the executable.',
      mbError, MB_OK
    );
    Result := False;
  end else
    Result := True;
end;
