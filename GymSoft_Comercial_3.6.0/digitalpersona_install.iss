{ DigitalPersona Runtime is an application component, never a standalone SDK.
  Keep an existing reader runtime intact when both native libraries already
  match this edition. Installing the vendor package requires Windows elevation. }

var
  DigitalPersonaRestartRequired: Boolean;

function RuntimeLibraryMatches(const Filename: String): Boolean;
var
  Data: AnsiString;
  PEOffset, Machine, VersionMS, VersionLS: Cardinal;
begin
  Result := False;
  if not GetVersionNumbers(Filename, VersionMS, VersionLS) then Exit;
  if (VersionMS < $00030004) or
     ((VersionMS = $00030004) and (VersionLS < $0000007F)) then Exit;
  if not LoadStringFromFile(Filename, Data) then Exit;
  if Length(Data) < 64 then Exit;
  if (Data[1] <> 'M') or (Data[2] <> 'Z') then Exit;
  PEOffset := Ord(Data[61]) + Ord(Data[62]) * 256 +
    Ord(Data[63]) * 65536 + Ord(Data[64]) * 16777216;
  if PEOffset > Cardinal(Length(Data) - 6) then Exit;
  if (Data[PEOffset + 1] <> 'P') or (Data[PEOffset + 2] <> 'E') or
     (Ord(Data[PEOffset + 3]) <> 0) or (Ord(Data[PEOffset + 4]) <> 0) then Exit;
  Machine := Ord(Data[PEOffset + 5]) + Ord(Data[PEOffset + 6]) * 256;
#if RuntimeBits == 64
  Result := Machine = $8664;
#else
  Result := Machine = $014C;
#endif
end;

function HasRuntimeInFolder(const Folder: String; Depth: Integer): Boolean;
var
  Entry: TFindRec;
  Child: String;
begin
  Result := False;
  if not DirExists(Folder) then Exit;
  if RuntimeLibraryMatches(AddBackslash(Folder) + 'dpfpdd.dll') and
     RuntimeLibraryMatches(AddBackslash(Folder) + 'dpfj.dll') then begin
    Log('Se conserva DigitalPersona existente: ' + Folder);
    Result := True;
    Exit;
  end;
  if Depth >= 8 then Exit;
  if FindFirst(AddBackslash(Folder) + '*', Entry) then begin
    try
      repeat
        if (Entry.Name <> '.') and (Entry.Name <> '..') and
           ((Entry.Attributes and FILE_ATTRIBUTE_DIRECTORY) <> 0) and
           ((Entry.Attributes and $0400) = 0) then begin
          Child := AddBackslash(Folder) + Entry.Name;
          if HasRuntimeInFolder(Child, Depth + 1) then begin
            Result := True;
            Exit;
          end;
        end;
      until not FindNext(Entry);
    finally
      FindClose(Entry);
    end;
  end;
end;

function DigitalPersonaRuntimeInstalled(): Boolean;
var
  ProgramRoot: String;
begin
#if RuntimeBits == 64
  ProgramRoot := ExpandConstant('{pf64}');
#else
  ProgramRoot := ExpandConstant('{pf32}');
#endif
  Result := HasRuntimeInFolder(ProgramRoot + '\DigitalPersona', 0) or
    HasRuntimeInFolder(ProgramRoot + '\HID Global', 0) or
    HasRuntimeInFolder(ProgramRoot + '\HID', 0) or
    (RuntimeLibraryMatches(ExpandConstant('{sys}\dpfpdd.dll')) and
     RuntimeLibraryMatches(ExpandConstant('{sys}\dpfj.dll')));
end;

procedure EnsureDigitalPersonaRuntime(const RuntimeFolder: String);
var
  SetupPath, LogFolder, LogPath, Parameters: String;
  ResultCode: Integer;
begin
  if DigitalPersonaRuntimeInstalled() then Exit;
  SetupPath := AddBackslash(RuntimeFolder) + 'setup.exe';
  if not FileExists(SetupPath) then
    RaiseException('Falta el componente completo DigitalPersona. Descarga de nuevo el instalador completo.');
  LogFolder := ExpandConstant('{localappdata}\AtlanticTechSoftware\logs');
  if not ForceDirectories(LogFolder) then
    RaiseException('No se pudo crear el registro de instalación DigitalPersona: ' + LogFolder);
  LogPath := AddBackslash(LogFolder) + 'DigitalPersona_instalacion.log';
  { InstallShield passes the quoted MSI log path using its documented /v syntax. }
  Parameters := '/s /v"REBOOT=ReallySuppress /qn /l*v \"' + LogPath + '\""';
  WizardForm.StatusLabel.Caption := 'Instalando el reconocimiento y controlador DigitalPersona...';
  if not ShellExec('runas', SetupPath, Parameters, RuntimeFolder, SW_SHOW,
      ewWaitUntilTerminated, ResultCode) then
    RaiseException('No se pudo instalar DigitalPersona (código ' + IntToStr(ResultCode) +
      '). Acepta la solicitud de Windows para instalar el controlador y vuelve a ejecutar el instalador.');
  if (ResultCode <> 0) and (ResultCode <> 3010) and (ResultCode <> 1641) then
    RaiseException('DigitalPersona no se instaló (código ' + IntToStr(ResultCode) +
      '). Revisa ' + LogPath + ' y vuelve a ejecutar el instalador.');
  if (ResultCode = 3010) or (ResultCode = 1641) then
    DigitalPersonaRestartRequired := True;
  if not DigitalPersonaRuntimeInstalled() then
    RaiseException('DigitalPersona terminó sin las bibliotecas compatibles con esta edición. Revisa ' +
      LogPath + ' antes de usar el lector.');
end;

function NeedRestart(): Boolean;
begin
  Result := DigitalPersonaRestartRequired;
end;
