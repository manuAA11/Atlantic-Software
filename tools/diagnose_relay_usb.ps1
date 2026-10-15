#requires -version 5.1
<#
Read-only Windows USB / Bluetooth incident collector.
Does not open COM ports, operate a relay, change devices, or change power settings.
Device instance identifiers are hashed before anything is written to disk.
#>
[CmdletBinding()]
param(
    [string]$OutputDirectory = '',
    [string]$DoorLogPath = ''
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Warnings = New-Object 'System.Collections.Generic.List[string]'
$script:RelevantClasses = @('USB', 'USBDevice', 'Ports', 'Bluetooth', 'MEDIA', 'AudioEndpoint', 'Sound', 'HIDClass')
$script:KnownProviders = @(
    'BTHUSB', 'BTHMINI', 'BTHPORT', 'BTHLEEnum',
    'Microsoft-Windows-Kernel-PnP', 'Microsoft-Windows-UserPnp',
    'Microsoft-Windows-USB-USBHUB3', 'Microsoft-Windows-USB-USBXHCI',
    'Microsoft-Windows-USB-UCX', 'Microsoft-Windows-Kernel-USB',
    'Microsoft-Windows-DriverFrameworks-UserMode',
    'Microsoft-Windows-DeviceSetupManager',
    'Microsoft-Windows-Bluetooth-Policy', 'Microsoft-Windows-Bluetooth-BthLEPrepairing',
    'Microsoft-Windows-Audio', 'Microsoft-Windows-AudioDeviceGraph'
)

function Read-Field($Object, [string]$Name) {
    if ($null -eq $Object) { return $null }
    $field = $Object.PSObject.Properties[$Name]
    if ($null -ne $field) { return $field.Value }
    return $null
}

function Add-CollectorWarning([string]$Text) {
    if (-not $script:Warnings.Contains($Text)) { [void]$script:Warnings.Add($Text) }
}

function Get-StableDeviceHash($Identifier) {
    if ([string]::IsNullOrWhiteSpace([string]$Identifier)) { return $null }
    $normalized = ([string]$Identifier).Trim().ToUpperInvariant()
    $algorithm = [System.Security.Cryptography.SHA256]::Create()
    try {
        $bytes = $algorithm.ComputeHash($script:Utf8.GetBytes($normalized))
        return ([System.BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
    } finally { $algorithm.Dispose() }
}

function Get-SafeNumber($Value, [long]$Maximum = 2147483647) {
    $number = [long]0
    if ($null -ne $Value -and [long]::TryParse([string]$Value, [ref]$number) -and $number -ge 0 -and $number -le $Maximum) {
        return $number
    }
    return $null
}

function Get-UsbFamily($Identifier) {
    if ([string]$Identifier -match '(?i)VID_([0-9A-F]{4}).*PID_([0-9A-F]{4})') {
        $usbVid, $usbPid = $Matches[1].ToUpperInvariant(), $Matches[2].ToUpperInvariant()
        return [pscustomobject][ordered]@{
            vid = $usbVid; pid = $usbPid
            ch340 = ($usbVid -eq '1A86' -and $usbPid -in @('7523', '5523'))
        }
    }
    return [pscustomobject][ordered]@{ vid = $null; pid = $null; ch340 = $false }
}

function Get-SafeStatus($Value) {
    $status = [string]$Value
    if ($status -in @('OK', 'Error', 'Unknown', 'Degraded', 'Pred Fail', 'Starting', 'Stopping', 'Service', 'Stressed', 'NonRecover', 'No Contact', 'Lost Comm')) {
        return $status
    }
    return 'NotReported'
}

function Get-LocalFilePath([string]$Path) {
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full.StartsWith('\\') -or $full.StartsWith('//')) { throw 'LOCAL_PATH_REQUIRED' }
    $rootPath = [System.IO.Path]::GetPathRoot($full)
    $drive = New-Object System.IO.DriveInfo($rootPath)
    if ($drive.DriveType -eq [System.IO.DriveType]::Network) { throw 'LOCAL_PATH_REQUIRED' }
    # Walk from the root, rejecting each existing reparse point BEFORE looking
    # below it. A local-looking junction must not redirect reads/writes to UNC.
    $inspectPaths = @($rootPath)
    $currentPath = $rootPath
    foreach ($part in @($full.Substring($rootPath.Length) -split '[\\/]' | Where-Object { $_ -ne '' })) {
        $currentPath = [System.IO.Path]::Combine($currentPath, $part)
        $inspectPaths += $currentPath
    }
    foreach ($candidatePath in $inspectPaths) {
        try { $attributes = [System.IO.File]::GetAttributes($candidatePath) }
        catch [System.IO.FileNotFoundException] { break }
        catch [System.IO.DirectoryNotFoundException] { break }
        if (($attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0) { throw 'LOCAL_PATH_REQUIRED' }
    }
    return $full
}

function Save-TechnicalJson([string]$Folder, [string]$Name, $Data) {
    $json = ConvertTo-Json -InputObject $Data -Depth 16
    [System.IO.File]::WriteAllText((Join-Path $Folder $Name), $json, $script:Utf8)
}

function Get-PnpSnapshot {
    $source, $collectionStatus = 'none', 'unavailable'
    $rawDevices = @()
    if (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) {
        try {
            $rawDevices = @(Get-CimInstance -ClassName Win32_PnPEntity -ErrorAction Stop)
            $source, $collectionStatus = 'Win32_PnPEntity/CIM', 'ok'
        } catch { }
    }
    if ($collectionStatus -ne 'ok' -and (Get-Command Get-WmiObject -ErrorAction SilentlyContinue)) {
        try {
            $rawDevices = @(Get-WmiObject -Class Win32_PnPEntity -ErrorAction Stop)
            $source, $collectionStatus = 'Win32_PnPEntity/WMI', 'ok'
        } catch { }
    }
    if ($collectionStatus -ne 'ok' -and (Get-Command Get-PnpDevice -ErrorAction SilentlyContinue)) {
        try {
            $rawDevices = @(Get-PnpDevice -ErrorAction Stop)
            $source, $collectionStatus = 'Get-PnpDevice', 'ok'
        } catch { }
    }
    if ($collectionStatus -ne 'ok') {
        Add-CollectorWarning 'No se pudo consultar el inventario PnP; no se solicitaron permisos elevados.'
    }
    $hasProperties = [bool](Get-Command Get-PnpDeviceProperty -ErrorAction SilentlyContinue)
    $propertyFailures = 0
    $rows = New-Object 'System.Collections.Generic.List[object]'
    foreach ($device in $rawDevices) {
        $identifier = Read-Field $device 'PNPDeviceID'
        if (-not $identifier) { $identifier = Read-Field $device 'DeviceID' }
        if (-not $identifier) { $identifier = Read-Field $device 'InstanceId' }
        if ([string]::IsNullOrWhiteSpace([string]$identifier)) { continue }
        $class = [string](Read-Field $device 'PNPClass')
        if (-not $class) { $class = [string](Read-Field $device 'Class') }
        if ($class -notin $script:RelevantClasses -and [string]$identifier -notmatch '^(?i)(USB|BTH[^\\]*)\\') { continue }
        if ($class -notin $script:RelevantClasses) { $class = 'OtherUSBorBluetooth' }
        $enumerator = (([string]$identifier -split '\\', 2)[0]).ToUpperInvariant()
        if ($enumerator -notin @('USB', 'BTH', 'BTHENUM', 'BTHLEDEVICE', 'BTHHFENUM', 'BTHLE', 'HDAUDIO', 'SWD', 'PCI', 'ROOT', 'HID', 'ACPI')) { $enumerator = 'Other' }
        $family = Get-UsbFamily $identifier
        $present = Read-Field $device 'Present'
        if ($present -isnot [bool]) { $present = $null }
        $problem = Get-SafeNumber (Read-Field $device 'ConfigManagerErrorCode') 65535
        $service = [string](Read-Field $device 'Service')
        if ($service -notmatch '^[A-Za-z0-9._-]{1,80}$') { $service = $null }
        $comPort = $null
        $name = [string](Read-Field $device 'Name')
        if (-not $name) { $name = [string](Read-Field $device 'FriendlyName') }
        if ($name -match '\bCOM[1-9][0-9]{0,3}\b') { $comPort = $Matches[0] }
        $parentHash, $driverVersion = $null, $null
        if ($hasProperties) {
            try {
                $properties = @(Get-PnpDeviceProperty -InstanceId ([string]$identifier) -KeyName @('DEVPKEY_Device_Parent', 'DEVPKEY_Device_ProblemCode', 'DEVPKEY_Device_DriverVersion') -ErrorAction Stop)
                foreach ($property in $properties) {
                    switch ([string](Read-Field $property 'KeyName')) {
                        'DEVPKEY_Device_Parent' { $parentHash = Get-StableDeviceHash (Read-Field $property 'Data') }
                        'DEVPKEY_Device_ProblemCode' { $problem = Get-SafeNumber (Read-Field $property 'Data') 65535 }
                        'DEVPKEY_Device_DriverVersion' {
                            $candidate = [string](Read-Field $property 'Data')
                            if ($candidate -match '^[0-9.]{1,40}$') { $driverVersion = $candidate }
                        }
                    }
                }
            } catch { $propertyFailures++ }
        }
        [void]$rows.Add([pscustomobject][ordered]@{
            device_hash = Get-StableDeviceHash $identifier
            parent_hash = $parentHash; class = $class; enumerator = $enumerator
            status = Get-SafeStatus (Read-Field $device 'Status')
            problem_code = $problem; present = $present; com_port = $comPort
            vid = $family.vid; pid = $family.pid; ch340 = $family.ch340
            service = $service; driver_version = $driverVersion
        })
    }
    if (-not $hasProperties -or $propertyFailures -gt 0) {
        Add-CollectorWarning 'Algunas relaciones de bus o versiones de controlador no estuvieron disponibles.'
    }
    return [pscustomobject][ordered]@{
        captured_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $collectionStatus; source = $source
        parent_property_cmdlet_available = $hasProperties
        property_query_failures = $propertyFailures
        devices = @($rows.ToArray() | Sort-Object device_hash)
    }
}

function Compare-PnpSnapshots($Before, $After) {
    if ($Before.status -ne 'ok' -or $After.status -ne 'ok') {
        return [pscustomobject][ordered]@{
            comparison_available = $false; added = @(); removed = @(); changed = @()
        }
    }
    $old, $new = @{}, @{}
    foreach ($row in $Before.devices) { $old[$row.device_hash] = $row }
    foreach ($row in $After.devices) { $new[$row.device_hash] = $row }
    $added, $removed, $changed = @(), @(), @()
    foreach ($key in @(@($old.Keys) + @($new.Keys) | Sort-Object -Unique)) {
        if (-not $old.ContainsKey($key)) { $added += $new[$key]; continue }
        if (-not $new.ContainsKey($key)) { $removed += $old[$key]; continue }
        $fields = @()
        foreach ($field in @('parent_hash', 'class', 'status', 'problem_code', 'present', 'com_port', 'service', 'driver_version')) {
            if ((Read-Field $old[$key] $field) -cne (Read-Field $new[$key] $field)) { $fields += $field }
        }
        if ($fields.Count -gt 0) {
            $changed += [pscustomobject][ordered]@{ device_hash = $key; fields = $fields; before = $old[$key]; after = $new[$key] }
        }
    }
    return [pscustomobject][ordered]@{
        comparison_available = ($Before.status -eq 'ok' -and $After.status -eq 'ok')
        added = $added; removed = $removed; changed = $changed
    }
}

function Get-SystemUsbEvents {
    $start = [DateTime]::UtcNow.AddMinutes(-20)
    $rows = New-Object 'System.Collections.Generic.List[object]'
    $status, $examined, $limitReached = 'unavailable', 0, $false
    if (Get-Command Get-WinEvent -ErrorAction SilentlyContinue) {
        try {
            # Cap work on noisy PCs. A reached cap is reported, never called complete.
            $events = @(Get-WinEvent -FilterHashtable @{ LogName = 'System'; StartTime = $start.ToLocalTime() } -MaxEvents 3000 -ErrorAction Stop)
            $examined, $limitReached, $status = $events.Count, ($events.Count -ge 3000), 'ok'
            foreach ($systemEvent in $events) {
                $provider = [string]$systemEvent.ProviderName
                if ($provider -notmatch '(?i)(USB|Bluetooth|^BTH|Kernel-PnP|UserPnp|DriverFrameworks|DeviceSetupManager|^Microsoft-Windows-Audio)') { continue }
                $providerLabel = $provider
                if ($provider -notin $script:KnownProviders) { $providerLabel = 'OtherUSBorBluetoothProvider' }
                $statusFields, $devices = [ordered]@{}, @()
                try {
                    # Do not read Message/FormatDescription or serialize this XML.
                    [xml]$xml = $systemEvent.ToXml()
                    foreach ($data in @($xml.SelectNodes("/*[local-name()='Event']/*[local-name()='EventData']/*[local-name()='Data']"))) {
                        $key, $value = [string]$data.GetAttribute('Name'), [string]$data.InnerText
                        if ($key -in @('Status', 'StatusCode', 'Problem', 'ProblemCode', 'ConfigManagerErrorCode', 'FailureStatus', 'ErrorCode', 'NtStatus', 'NTStatus', 'Win32Error', 'HRESULT', 'HResult', 'Result', 'ReasonCode', 'PortNumber')) {
                            if ($value -match '^(0x[0-9A-Fa-f]{1,16}|[0-9]{1,20}|-[0-9]{1,19})$') { $statusFields[$key] = $value }
                        } elseif ($key -in @('DeviceInstanceId', 'DeviceInstanceID', 'DeviceId', 'DeviceID', 'InstanceId', 'InstanceID', 'DeviceInstance', 'ParentId', 'ParentID')) {
                            if (-not [string]::IsNullOrWhiteSpace($value)) {
                                $family = Get-UsbFamily $value
                                $devices += [pscustomobject][ordered]@{ field = $key; device_hash = Get-StableDeviceHash $value; vid = $family.vid; pid = $family.pid }
                            }
                        }
                    }
                } catch { }
                [void]$rows.Add([pscustomobject][ordered]@{
                    at_utc = $systemEvent.TimeCreated.ToUniversalTime().ToString('o')
                    provider = $providerLabel; id = Get-SafeNumber $systemEvent.Id 65535
                    level = Get-SafeNumber $systemEvent.Level 255
                    record_id = Get-SafeNumber $systemEvent.RecordId ([long]::MaxValue)
                    task = Get-SafeNumber $systemEvent.Task 65535; opcode = Get-SafeNumber $systemEvent.Opcode 255
                    status_fields = [pscustomobject]$statusFields; devices = $devices
                })
            }
        } catch {
            if ([string]$_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*') { $status = 'ok' }
            else { $status = 'unavailable' }
        }
    }
    if ($status -ne 'ok') { Add-CollectorWarning 'No se pudieron leer los eventos System; se conservaron las otras consultas sin elevar permisos.' }
    if ($limitReached) { Add-CollectorWarning 'System alcanzo el limite de 3000 eventos; la ventana de 20 minutos puede estar incompleta.' }
    return [pscustomobject][ordered]@{
        status = $status; window_start_utc = $start.ToString('o')
        window_end_utc = [DateTime]::UtcNow.ToString('o')
        system_events_examined = $examined; cap_reached = $limitReached
        events = $rows.ToArray()
    }
}

function Get-SanitizedDoorLog([string]$Path) {
    $allowedEvents = @('relay_cancel_failed', 'relay_rest_sent', 'relay_unlock_end', 'relay_rest_failed', 'relay_close_failed', 'relay_close_timeout', 'relay_close_monitor_unavailable', 'relay_rest_start', 'relay_unlock_start', 'relay_error', 'relay_disconnected', 'relay_reconnected_requires_rest', 'reader_probe', 'reader_probe_failed', 'backend_error', 'backend_invalid_response', 'access_response_expired', 'read_completion_log_failed')
    $allowedStages = @('configuration', 'port_identity', 'serial_open', 'initial_rest_write', 'initial_rest_drain', 'unlock_write', 'unlock_drain', 'final_rest_write', 'final_rest_drain', 'final_rest', 'serial_close', 'serial', 'reader', 'backend', 'deduplication')
    $allowedTypes = @('OSError', 'PermissionError', 'FileNotFoundError', 'TimeoutError', 'ValueError', 'TypeError', 'SerialException', 'SerialTimeoutException', 'PortNotOpenError', 'ImportError', 'ModuleNotFoundError', 'Error')
    $rows = New-Object 'System.Collections.Generic.List[object]'
    $status, $discarded = 'not_found', 0
    try {
        $localPath = Get-LocalFilePath $Path
        if (Test-Path -LiteralPath $localPath -PathType Leaf) {
            $lines = @(Get-Content -LiteralPath $localPath -Encoding UTF8 -Tail 500 -ErrorAction Stop)
            $status = 'ok'
            foreach ($line in $lines) {
                try { $record = ConvertFrom-Json -InputObject $line -ErrorAction Stop }
                catch { $discarded++; continue }
                $eventName = [string](Read-Field $record 'event')
                if ($eventName -notin $allowedEvents) { $discarded++; continue }
                $safe = [ordered]@{ event = $eventName }
                $instant = [DateTimeOffset]::MinValue
                $atValue = Read-Field $record 'at'
                if ($atValue -is [DateTimeOffset]) {
                    $safe['at_utc'] = $atValue.UtcDateTime.ToString('o')
                } elseif ($atValue -is [DateTime]) {
                    # Newer PowerShell JSON readers can produce DateTime. Never
                    # invent a timezone for an unspecified wall-clock value.
                    if ($atValue.Kind -ne [DateTimeKind]::Unspecified) { $safe['at_utc'] = $atValue.ToUniversalTime().ToString('o') }
                } else {
                    $at = [string]$atValue
                    if ($at -match '^\d{4}-\d{2}-\d{2}T.+(Z|[+-]\d{2}:\d{2})$' -and [DateTimeOffset]::TryParse($at, [ref]$instant)) { $safe['at_utc'] = $instant.UtcDateTime.ToString('o') }
                }
                $port = [string](Read-Field $record 'port')
                if ($port -match '^COM[1-9][0-9]{0,3}$') { $safe['port'] = $port }
                $stage = [string](Read-Field $record 'stage')
                if ($stage -in $allowedStages) { $safe['stage'] = $stage }
                $kind = [string](Read-Field $record 'error_type')
                $legacyError = [string](Read-Field $record 'error')
                if (-not $kind -and $legacyError -in $allowedTypes) { $kind = $legacyError }
                if ($kind -in $allowedTypes) { $safe['error_type'] = $kind }
                if ($legacyError -in @('USB_DISCONNECTED', 'STALE_AUTHORIZATION')) { $safe['error_code'] = $legacyError }
                foreach ($key in @('errno', 'winerror')) {
                    $number = Get-SafeNumber (Read-Field $record $key) 65535
                    if ($null -ne $number) { $safe[$key] = $number }
                }
                $command = [string](Read-Field $record 'command')
                if ($command -in @('a00100a1', 'a00101a2')) { $safe['command'] = $command.ToLowerInvariant() }
                $state = [string](Read-Field $record 'state')
                if ($state -in @('Desconocido', 'Desconocido; cierre USB pendiente', 'Reposo (OFF enviado)', 'Liberando (ON enviado)')) { $safe['state'] = $state }
                $reason = [string](Read-Field $record 'reason')
                if ($reason -in @('shutdown', 'watchdog', 'finally', 'manual', 'test', 'access')) { $safe['reason'] = $reason }
                [void]$rows.Add([pscustomobject]$safe)
            }
        }
    } catch { $status = 'unavailable' }
    if ($status -ne 'ok') { Add-CollectorWarning 'No se pudo leer un puerta.log local; no se copiaron configuraciones ni archivos alternativos.' }
    return [pscustomobject][ordered]@{
        status = $status; maximum_lines_read = 500; discarded_lines = $discarded
        note = 'Only explicitly permitted technical fields; no raw log or free-form error text.'
        events = $rows.ToArray()
    }
}

function Get-SystemMetadata {
    $version, $build = [Environment]::OSVersion.Version.ToString(), [Environment]::OSVersion.Version.Build.ToString()
    if (Get-Command Get-CimInstance -ErrorAction SilentlyContinue) {
        try {
            $os = Get-CimInstance -ClassName Win32_OperatingSystem -ErrorAction Stop
            if ([string]$os.Version -match '^[0-9.]+$') { $version = [string]$os.Version }
            if ([string]$os.BuildNumber -match '^[0-9]+$') { $build = [string]$os.BuildNumber }
        } catch { }
    }
    return [pscustomobject][ordered]@{
        os_version = $version; os_build = $build
        os_bits = $(if ([Environment]::Is64BitOperatingSystem) { 64 } else { 32 })
        collector_process_bits = ([IntPtr]::Size * 8)
        powershell_version = $PSVersionTable.PSVersion.ToString()
        machine_name_collected = $false; user_name_collected = $false
    }
}

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) { throw 'WINDOWS_REQUIRED' }
    if (-not $OutputDirectory) {
        $base = [Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)
        $OutputDirectory = Join-Path $base ('Atlantic Tech Software\DiagnosticoUSB\' + [DateTime]::Now.ToString('yyyyMMdd_HHmmss') + '_' + [Guid]::NewGuid().ToString('N').Substring(0, 8))
    }
    $folder = Get-LocalFilePath $OutputDirectory
    if (Test-Path -LiteralPath $folder) { throw 'NEW_OUTPUT_FOLDER_REQUIRED' }
    [void][System.IO.Directory]::CreateDirectory($folder)
    if (-not $DoorLogPath) {
        $DoorLogPath = Join-Path ([Environment]::GetFolderPath([Environment+SpecialFolder]::LocalApplicationData)) 'GymControl\puerta\puerta.log'
    }
    $started = [DateTime]::UtcNow
    $metadata = Get-SystemMetadata
    Write-Host 'Diagnostico USB / Bluetooth - solo lectura, sin privilegios de administrador.'
    Write-Host 'No abre puertos COM, no envia pulsos y no cambia dispositivos ni energia.'
    Write-Host 'Tomando fotografia ANTES...'
    $before = Get-PnpSnapshot
    Save-TechnicalJson $folder 'antes.json' $before
    Save-TechnicalJson $folder 'sistema.json' $metadata
    Write-Host ''
    Write-Host 'Realice por separado, desde ZTATTUZ, la operacion normal que iba a realizar.'
    Write-Host 'Este programa no inicia ninguna prueba de puerta. No repita asistencias para el colector.'
    [void](Read-Host 'Al terminar o aparecer el fallo, vuelva aqui y pulse ENTER para tomar DESPUES')
    Write-Host 'Tomando fotografia DESPUES y eventos tecnicos...'
    $after = Get-PnpSnapshot
    $changes = Compare-PnpSnapshots $before $after
    $systemEvents = Get-SystemUsbEvents
    $doorEvents = Get-SanitizedDoorLog $DoorLogPath
    if (([DateTime]::UtcNow - $started).TotalMinutes -gt 20) { Add-CollectorWarning 'La sesion duro mas de 20 minutos; algunos eventos iniciales quedan fuera de la ventana System.' }
    Save-TechnicalJson $folder 'despues.json' $after
    Save-TechnicalJson $folder 'cambios.json' $changes
    Save-TechnicalJson $folder 'eventos_system.json' $systemEvents
    Save-TechnicalJson $folder 'puerta_sanitizada.json' $doorEvents
    $partial = ($script:Warnings.Count -gt 0)
    $summary = [pscustomobject][ordered]@{
        schema = 1; collector = 'Atlantic USB Bluetooth read-only'
        started_at_utc = $started.ToString('o'); finished_at_utc = [DateTime]::UtcNow.ToString('o')
        status = $(if ($partial) { 'partial' } else { 'collected' })
        architecture = $metadata
        before_status = $before.status; after_status = $after.status
        before_devices = @($before.devices).Count; after_devices = @($after.devices).Count
        comparison_available = $changes.comparison_available
        added = $(if ($changes.comparison_available) { @($changes.added).Count } else { $null })
        removed = $(if ($changes.comparison_available) { @($changes.removed).Count } else { $null })
        changed = $(if ($changes.comparison_available) { @($changes.changed).Count } else { $null })
        system_event_status = $systemEvents.status; relevant_system_events = @($systemEvents.events).Count
        sanitized_door_log_status = $doorEvents.status; sanitized_door_events = @($doorEvents.events).Count
        warnings = $script:Warnings.ToArray()
        physical_cause_confirmed = $false
        hardware_actions_performed = $false
    }
    Save-TechnicalJson $folder 'resumen.json' $summary
    $deltaLine = 'Comparacion no disponible: no se infieren altas, bajas ni cambios con una fotografia incompleta.'
    if ($changes.comparison_available) { $deltaLine = 'Altas/bajas/cambios: ' + $summary.added + ' / ' + $summary.removed + ' / ' + $summary.changed }
    $text = @(
        'Atlantic Tech Software - Diagnostico USB / Bluetooth',
        'Coleccion tecnica de solo lectura. Causa fisica NO confirmada.',
        ('Estado: ' + $summary.status),
        ('Windows: ' + $metadata.os_bits + ' bits. Colector: ' + $metadata.collector_process_bits + ' bits. PowerShell: ' + $metadata.powershell_version),
        ('Dispositivos antes/despues: ' + $summary.before_devices + ' / ' + $summary.after_devices),
        $deltaLine,
        ('Eventos System relevantes (ultimos 20 minutos): ' + $summary.relevant_system_events),
        ('Eventos de puerta conservados sin datos personales: ' + $summary.sanitized_door_events),
        '',
        'No abre COM, no opera el rele, no cambia energia ni reinicia dispositivos.',
        'No incluye nombres de usuario/equipo, IDs de miembro/gimnasio, seriales, mensajes libres ni configuraciones.',
        'Los hashes estables permiten correlacionar dispositivos entre las dos fotografias.',
        'No observar cambios entre fotografias no descarta una desconexion transitoria.',
        '',
        'Limitaciones de esta coleccion:'
    )
    if ($partial) { $text += $script:Warnings.ToArray() }
    else { $text += 'Las consultas terminaron; esto no valida el cableado, la alimentacion ni el controlador fisico.' }
    [System.IO.File]::WriteAllLines((Join-Path $folder 'RESUMEN.txt'), [string[]]$text, $script:Utf8)
    Write-Host ''
    Write-Host ('Resultado: ' + $summary.status + '. Revise RESUMEN.txt y conserve todos los JSON.')
    Write-Host ('Carpeta local: ' + $folder)
    if ($partial) { exit 2 }
    exit 0
} catch {
    # Exception messages can contain usernames, file paths or raw device IDs.
    Write-Host 'No se pudo completar el colector. No se modificaron dispositivos ni ajustes.'
    Write-Host 'Use Windows PowerShell 5.1 y una carpeta local nueva con permiso de escritura.'
    Write-Host 'Si el sistema impide ejecutar scripts, solicite autorizacion al responsable del equipo.'
    exit 1
}
