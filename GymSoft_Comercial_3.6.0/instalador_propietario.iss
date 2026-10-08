#ifndef AppVersion
#define AppVersion "3.6.0"
#endif
[Setup]
AppId={{58D6DD62-FD67-4CC1-8D87-153AFB4EE44A}
AppName=Atlantic Gym · Control comercial
AppVersion={#AppVersion}
AppPublisher=Atlantic Tech Software
DefaultDirName={localappdata}\Programs\GymSoftControl
DefaultGroupName=Gym soft Propietario
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=salida
OutputBaseFilename=GymSoft_Propietario_PRIVADO_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=icono.ico
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\GymSoftControl.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "dist\GymSoftControl\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icono.ico"; DestDir: "{app}"; DestName: "GymSoft-{#AppVersion}.ico"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Atlantic Gym Propietario"; Filename: "{app}\GymSoftControl.exe"; WorkingDir: "{app}"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Propietario"
Name: "{autodesktop}\Atlantic Gym Propietario"; Filename: "{app}\GymSoftControl.exe"; WorkingDir: "{app}"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Propietario"

[Run]
Filename: "{app}\GymSoftControl.exe"; Description: "Abrir panel del propietario"; Flags: nowait postinstall skipifsilent unchecked

[Code]
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SHChangeNotify($08000000, 0, 0, 0);
end;
