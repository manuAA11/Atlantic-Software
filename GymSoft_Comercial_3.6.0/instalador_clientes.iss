#ifndef BuildDistRoot
#define BuildDistRoot "dist"
#endif
#ifndef BuildComponentRoot
#define BuildComponentRoot "salida\componentes"
#endif
#ifdef BuildValidation
#define BuildSuffix " · Validación técnica (no final)"
#else
#define BuildSuffix ""
#endif
#define RuntimeBits 64
#ifndef AppVersion
#define AppVersion "3.6.0"
#endif
[Setup]
AppId={{6C58E8B8-C2ED-4B60-A080-EEA57BB407C2}
AppName=Atlantic Gym{#BuildSuffix}
AppVersion={#AppVersion}
AppPublisher=Atlantic Tech Software
#ifdef BuildValidation
VersionInfoDescription=Atlantic Gym · Validación técnica (no final)
VersionInfoProductName=Atlantic Gym · Validación técnica (no final)
#endif
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
MinVersion=10.0
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
LicenseFile=DigitalPersonaRuntime\Licenses\EULA SDK.rtf
SetupIconFile=icono.ico
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\Admin\GymSoftAdmin.exe

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{app}\DigitalPersonaRuntime"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BuildDistRoot}\GymSoftAdmin\*"; DestDir: "{app}\Admin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#BuildDistRoot}\GymSoftRecepcion\*"; DestDir: "{app}\Recepcion"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icono.ico"; DestDir: "{app}\Admin"; Flags: ignoreversion
Source: "icono_recepcion.ico"; DestDir: "{app}\Recepcion"; Flags: ignoreversion
Source: "icono_recepcion.ico"; DestDir: "{app}"; DestName: "GymSoft-Recepcion-{#AppVersion}.ico"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}\Recepcion"; Flags: ignoreversion
Source: "icono.ico"; DestDir: "{app}"; DestName: "GymSoft-{#AppVersion}.ico"; Flags: ignoreversion
Source: "COPYRIGHT.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Atlantic Gym Administrador"; Filename: "{app}\Admin\GymSoftAdmin.exe"; WorkingDir: "{app}\Admin"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Administracion"
Name: "{group}\Atlantic Gym Recepción"; Filename: "{app}\Recepcion\GymSoftRecepcion.exe"; WorkingDir: "{app}\Recepcion"; IconFilename: "{app}\GymSoft-Recepcion-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Recepcion"
Name: "{autodesktop}\Atlantic Gym Administrador"; Filename: "{app}\Admin\GymSoftAdmin.exe"; WorkingDir: "{app}\Admin"; IconFilename: "{app}\GymSoft-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Administracion"
Name: "{autodesktop}\Atlantic Gym Recepción"; Filename: "{app}\Recepcion\GymSoftRecepcion.exe"; WorkingDir: "{app}\Recepcion"; IconFilename: "{app}\GymSoft-Recepcion-{#AppVersion}.ico"; IconIndex: 0; AppUserModelID: "GymSoft.Comercial.Recepcion"

[Run]
Filename: "{app}\Admin\GymSoftAdmin.exe"; Description: "Abrir Gym soft Administración"; Flags: nowait postinstall skipifsilent unchecked

[Code]
#include "digitalpersona_install.iss"
procedure SHChangeNotify(wEventId: Integer; uFlags: Cardinal; dwItem1, dwItem2: Integer);
  external 'SHChangeNotify@shell32.dll stdcall';

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    EnsureDigitalPersonaRuntime(ExpandConstant('{app}\DigitalPersonaRuntime'));
    SHChangeNotify($08000000, 0, 0, 0);
  end;
end;
