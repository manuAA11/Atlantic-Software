#ifndef AppVersion
#define AppVersion "3.6.1"
#endif
[Setup]
AppId=ZTATTUZActualizadorCompleto
AppName=Atlantic Gym · ZTATTUZ
AppVersion={#AppVersion}
AppPublisher=Atlantic Tech Software
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
SetupIconFile=icono.ico
DisableReadyPage=no
[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
[Files]
Source: "DigitalPersonaRuntime\*"; DestDir: "{tmp}\DigitalPersonaRuntime"; Flags: deleteafterinstall recursesubdirs createallsubdirs
Source: "salida\componentes\ZTATTUZ_Admin_{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
Source: "salida\componentes\ZTATTUZ_Recepcion_{#AppVersion}.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall
[Code]
procedure InstallComponent(const Filename: String; const LabelText: String);
var Code: Integer;
begin
  WizardForm.StatusLabel.Caption := LabelText;
  if not Exec(ExpandConstant('{tmp}\') + Filename, '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /CLOSEAPPLICATIONS /LOG', '', SW_SHOW, ewWaitUntilTerminated, Code) then
    RaiseException('No se pudo abrir el instalador de ' + LabelText + '. Vuelve a ejecutar la actualización.');
  if (Code <> 0) and (Code <> 3010) then
    RaiseException('No se completó ' + LabelText + ' (código ' + IntToStr(Code) + '). Cierra las aplicaciones y vuelve a ejecutar la actualización.');
end;
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then begin
    InstallComponent('ZTATTUZ_Admin_{#AppVersion}.exe', 'Administración');
    InstallComponent('ZTATTUZ_Recepcion_{#AppVersion}.exe', 'Recepción');
  end;
end;

[Run]
Filename: "{tmp}\DigitalPersonaRuntime\setup.exe"; WorkingDir: "{tmp}\DigitalPersonaRuntime"; Description: "Instalar el controlador y reconocimiento DigitalPersona (no requiere lector conectado)"; Verb: "runas"; Flags: shellexec postinstall skipifsilent waituntilterminated
