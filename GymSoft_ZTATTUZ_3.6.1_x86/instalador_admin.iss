#ifndef AppVersion
#define AppVersion "3.6.1"
#endif
[Setup]
AppId={{E89DF404-FD78-4A97-89E8-9BA23D3B0B19}
AppName=Atlantic Gym · ZTATTUZ Administrador
AppVersion={#AppVersion}
AppPublisher=Atlantic Tech Software
DefaultDirName={localappdata}\Programs\ZTATTUZ Admin
DefaultGroupName=ZTATTUZ
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=salida\componentes
OutputBaseFilename=ZTATTUZ_Admin_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
ArchitecturesAllowed=x86os
SetupIconFile=icono.ico
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\ZTATTUZ Admin.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{app}\DigitalPersonaRuntime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\ZTATTUZ Admin\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icono.ico"; DestDir: "{app}"; DestName: "ZTATTUZ-{#AppVersion}.ico"; Flags: ignoreversion
Source: "COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_WINDOWS_MINI.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_ACTUALIZAR_{#AppVersion}.md"; DestDir: "{app}"; Flags: ignoreversion

Source: "GUIA_PUERTA_LCUS1.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Atlantic Gym · ZTATTUZ Administrador"; Filename: "{app}\ZTATTUZ Admin.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Administracion"
Name: "{autodesktop}\Atlantic Gym · ZTATTUZ Administrador"; Filename: "{app}\ZTATTUZ Admin.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Administracion"
Name: "{group}\Diagnóstico de Atlantic Gym · ZTATTUZ Administrador"; Filename: "{app}\ZTATTUZ Admin.exe"; Parameters: "--diagnostico"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Administracion"

[Code]
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then SHChangeNotify($08000000, 0, 0, 0);
end;

[Run]
Filename: "{app}\DigitalPersonaRuntime\setup.exe"; WorkingDir: "{app}\DigitalPersonaRuntime"; Description: "Instalar el controlador y reconocimiento DigitalPersona (no requiere lector conectado)"; Verb: "runas"; Flags: shellexec postinstall skipifsilent waituntilterminated
