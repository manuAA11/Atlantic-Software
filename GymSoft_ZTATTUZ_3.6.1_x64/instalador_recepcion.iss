#ifndef AppVersion
#define AppVersion "3.6.1"
#endif
[Setup]
AppId={{8F529E62-5D29-49E0-99AA-28255D920ECE}
AppName=ZTATTUZ Recepción
AppVersion={#AppVersion}
AppPublisher=Manuel Cuéllar
DefaultDirName={localappdata}\Programs\ZTATTUZ Recepcion
DefaultGroupName=ZTATTUZ
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=salida\componentes
OutputBaseFilename=ZTATTUZ_Recepcion_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
SetupIconFile=icono.ico
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\ZTATTUZ Recepcion.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{app}\DigitalPersonaRuntime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\ZTATTUZ Recepcion\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icono.ico"; DestDir: "{app}"; DestName: "ZTATTUZ-{#AppVersion}.ico"; Flags: ignoreversion
Source: "COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_WINDOWS_MINI.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "LEEME_ACTUALIZAR_{#AppVersion}.md"; DestDir: "{app}"; Flags: ignoreversion

Source: "GUIA_PUERTA_LCUS1.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\ZTATTUZ Recepción"; Filename: "{app}\ZTATTUZ Recepcion.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Recepcion"
Name: "{autodesktop}\ZTATTUZ Recepción"; Filename: "{app}\ZTATTUZ Recepcion.exe"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Recepcion"
Name: "{group}\Diagnóstico de ZTATTUZ Recepción"; Filename: "{app}\ZTATTUZ Recepcion.exe"; Parameters: "--diagnostico"; WorkingDir: "{app}"; IconFilename: "{app}\ZTATTUZ-{#AppVersion}.ico"; AppUserModelID: "ZTATTUZ.Recepcion"

[Code]
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then SHChangeNotify($08000000, 0, 0, 0);
end;

[Run]
Filename: "{app}\DigitalPersonaRuntime\setup.exe"; WorkingDir: "{app}\DigitalPersonaRuntime"; Description: "Instalar el controlador y reconocimiento DigitalPersona (no requiere lector conectado)"; Verb: "runas"; Flags: shellexec postinstall skipifsilent waituntilterminated
