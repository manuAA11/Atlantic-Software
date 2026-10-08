#ifndef AppVersion
#define AppVersion "3.6.0"
#endif
[Setup]
AppId={{6C58E8B8-C2ED-4B60-A080-EEA57BB407C2}
AppName=Gym soft
AppVersion={#AppVersion}
AppPublisher=Gym soft
DefaultDirName={localappdata}\Programs\GymSoftCommercial
DefaultGroupName=Gym soft
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
UsePreviousAppDir=yes
OutputDir=salida
OutputBaseFilename=GymSoft_Instalar_o_Actualizar_{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
SetupIconFile=icono.ico
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\Admin\GymSoftAdmin.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{app}\DigitalPersonaRuntime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\GymSoftAdmin\*"; DestDir: "{app}\Admin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\GymSoftRecepcion\*"; DestDir: "{app}\Recepcion"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icono.ico"; DestDir: "{app}\Admin"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}\Recepcion"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}"; DestName: "GymSoft-{#AppVersion}.ico"; Flags: ignoreversion
Source: "COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Gym soft Administración"; Filename: "{app}\Admin\GymSoftAdmin.exe"; WorkingDir: "{app}\Admin"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Administracion"
Name: "{group}\Gym soft Recepción"; Filename: "{app}\Recepcion\GymSoftRecepcion.exe"; WorkingDir: "{app}\Recepcion"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Recepcion"
Name: "{autodesktop}\Gym soft Administración"; Filename: "{app}\Admin\GymSoftAdmin.exe"; WorkingDir: "{app}\Admin"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Administracion"
Name: "{autodesktop}\Gym soft Recepción"; Filename: "{app}\Recepcion\GymSoftRecepcion.exe"; WorkingDir: "{app}\Recepcion"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Recepcion"

[Run]
Filename: "{app}\DigitalPersonaRuntime\setup.exe"; WorkingDir: "{app}\DigitalPersonaRuntime"; Description: "Instalar el controlador y reconocimiento DigitalPersona (no requiere lector conectado)"; Verb: "runas"; Flags: shellexec postinstall skipifsilent waituntilterminated
Filename: "{app}\Admin\GymSoftAdmin.exe"; Description: "Abrir Gym soft Administración"; Flags: nowait postinstall skipifsilent unchecked

[Code]
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    SHChangeNotify($08000000, 0, 0, 0);
end;
