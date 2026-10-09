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
#define AppVersion "3.6.1"
#endif
[Setup]
AppId=ZTATTUZActualizadorCompleto
AppName=Atlantic Gym · ZTATTUZ{#BuildSuffix}
AppVersion={#AppVersion}
AppPublisher=Atlantic Tech Software
#ifdef BuildValidation
VersionInfoDescription=Atlantic Gym · Validación técnica (no final)
VersionInfoProductName=Atlantic Gym · Validación técnica (no final)
#endif
CreateAppDir=no
Uninstallable=no
PrivilegesRequired=lowest
OutputDir=salida
OutputBaseFilename=ZTATTUZ_Instalar_o_Actualizar_{#AppVersion}_x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
ArchitecturesAllowed=x64os
ArchitecturesInstallIn64BitMode=x64os
LicenseFile=DigitalPersonaRuntime\Licenses\EULA SDK.rtf
SetupIconFile=icono.ico
DisableReadyPage=no
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{tmp}\DigitalPersonaRuntime"; Flags: deleteafterinstall recursesubdirs createallsubdirs
Source: "{#BuildComponentRoot}\ZTATTUZ_Admin_{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "{#BuildComponentRoot}\ZTATTUZ_Recepcion_{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Code]
#include "digitalpersona_install.iss"
procedure InstallComponent(const Filename: String; const LabelText: String);
var Code: Integer;
begin
  WizardForm.StatusLabel.Caption := LabelText;
  if not Exec(ExpandConstant('{tmp}\') + Filename, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /LOG', '', SW_SHOW, ewWaitUntilTerminated, Code) then
    RaiseException('No se pudo abrir el instalador de ' + LabelText + '. Vuelve a ejecutar la actualización.');
  if (Code <> 0) and (Code <> 3010) then
    RaiseException('No se completó ' + LabelText + ' (código ' + IntToStr(Code) + '). Cierra las aplicaciones y vuelve a ejecutar la actualización.');
  if Code = 3010 then DigitalPersonaRestartRequired := True;
end;
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    EnsureDigitalPersonaRuntime(ExpandConstant('{tmp}\DigitalPersonaRuntime'));
    InstallComponent('ZTATTUZ_Admin_{#AppVersion}.exe', 'Administración');
    InstallComponent('ZTATTUZ_Recepcion_{#AppVersion}.exe', 'Recepción');
  end;
end;
