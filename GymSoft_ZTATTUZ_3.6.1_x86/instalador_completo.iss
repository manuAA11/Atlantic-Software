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
#define RuntimeBits 32
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
OutputBaseFilename=ZTATTUZ_Instalar_o_Actualizar_{#AppVersion}_x86
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
MinVersion=10.0
ArchitecturesAllowed=x86os
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
procedure InstallComponent(const Filename: String; const LabelText: String; const Role: String);
var
  Code: Integer;
  Parameters: String;
#ifdef BuildValidation
  QAInstallRoot: String;
#endif
begin
  WizardForm.StatusLabel.Caption := LabelText;
  Parameters := '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /LOG';
#ifdef BuildValidation
  { Only the technical runner can supply its marked, exclusive test directory.
    Without this parameter, Inno keeps the existing component directories. }
  QAInstallRoot := ExpandConstant('{param:QAInstallRoot|}');
  if QAInstallRoot <> '' then begin
    if (Pos('"', QAInstallRoot) <> 0) or (Length(QAInstallRoot) < 3) or
       (QAInstallRoot[2] <> ':') or (QAInstallRoot[3] <> '\') or
       not DirExists(QAInstallRoot) or
       not FileExists(AddBackslash(QAInstallRoot) + 'ATLANTIC_EPHEMERAL_INSTALLATION.json') then
      RaiseException('La carpeta de instalación técnica no pertenece a la prueba efímera.');
    Parameters := Parameters + ' /DIR="' + AddBackslash(QAInstallRoot) + Role + '"';
  end;
#endif
  if not Exec(ExpandConstant('{tmp}\') + Filename, Parameters, '', SW_SHOW, ewWaitUntilTerminated, Code) then
    RaiseException('No se pudo abrir el instalador de ' + LabelText + '. Vuelve a ejecutar la actualización.');
  if (Code <> 0) and (Code <> 3010) then
    RaiseException('No se completó ' + LabelText + ' (código ' + IntToStr(Code) + '). Cierra las aplicaciones y vuelve a ejecutar la actualización.');
  if Code = 3010 then DigitalPersonaRestartRequired := True;
end;
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    EnsureDigitalPersonaRuntime(ExpandConstant('{tmp}\DigitalPersonaRuntime'));
    InstallComponent('ZTATTUZ_Admin_{#AppVersion}.exe', 'Administración', 'admin');
    InstallComponent('ZTATTUZ_Recepcion_{#AppVersion}.exe', 'Recepción', 'reception');
  end;
end;
