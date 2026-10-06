#define AppVersion GetEnv("APP_VERSION")

[Setup]
AppId={{8F3C2A1E-6B4D-4E2A-9C7F-1D2E3F4A5B6C}
AppName=INTC Print Bridge
AppVersion={#AppVersion}
AppPublisher=INTC
DefaultDirName={autopf}\INTC Print Bridge
DefaultGroupName=INTC Print Bridge
OutputDir=..\Output
OutputBaseFilename=INTC-Bridge-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Files]
Source: "..\dist\INTCBridgeService\*"; DestDir: "{app}\service"; Flags: recursesubdirs ignoreversion
Source: "..\dist\INTCBridge\*"; DestDir: "{app}\gui"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{group}\INTC Print Bridge"; Filename: "{app}\gui\INTCBridge.exe"
Name: "{autodesktop}\INTC Print Bridge"; Filename: "{app}\gui\INTCBridge.exe"

[Run]
Filename: "{app}\service\INTCBridgeService.exe"; Parameters: "--startup auto install"; Flags: runhidden waituntilterminated
Filename: "{sys}\sc.exe"; Parameters: "failure INTCPrintBridge reset= 86400 actions= restart/5000/restart/5000/restart/5000"; Flags: runhidden waituntilterminated
Filename: "{app}\service\INTCBridgeService.exe"; Parameters: "start"; Flags: runhidden waituntilterminated
Filename: "{app}\gui\INTCBridge.exe"; Description: "Ouvrir INTC Print Bridge"; Flags: postinstall nowait skipifsilent shellexec

[UninstallRun]
Filename: "{app}\service\INTCBridgeService.exe"; Parameters: "stop"; Flags: runhidden waituntilterminated; RunOnceId: "StopSvc"
Filename: "{app}\service\INTCBridgeService.exe"; Parameters: "remove"; Flags: runhidden waituntilterminated; RunOnceId: "RemoveSvc"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  R: Integer;
begin
  { Mise à jour : on arrête l'ancien service pour libérer ses fichiers }
  Exec(ExpandConstant('{sys}\sc.exe'), 'stop INTCPrintBridge', '', SW_HIDE, ewWaitUntilTerminated, R);
  Sleep(2000);
  Result := '';
end;
