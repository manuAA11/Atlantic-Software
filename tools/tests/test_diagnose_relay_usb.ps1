[CmdletBinding()]
param([string]$CollectorPath = (Join-Path (Split-Path $PSScriptRoot -Parent) 'diagnose_relay_usb.ps1'))
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$script:CheckCount = 0
function Assert-Check([bool]$Condition, [string]$Label) {
    if (-not $Condition) { throw ('QA failed: ' + $Label) }
    $script:CheckCount++
}
$tokens, $parseErrors = $null, $null
$collectorAst = [System.Management.Automation.Language.Parser]::ParseFile($CollectorPath, [ref]$tokens, [ref]$parseErrors)
Assert-Check ($parseErrors.Count -eq 0) 'PowerShell parser accepts collector'
# Only function definitions and the four literal fixture/configuration values
# are loaded. The Windows collector main block and Read-Host never execute.
$constants = @('$script:Utf8', '$script:Warnings', '$script:RelevantClasses', '$script:KnownProviders')
foreach ($statement in $collectorAst.EndBlock.Statements) {
    if ($statement -is [System.Management.Automation.Language.AssignmentStatementAst] -and $statement.Left.Extent.Text -in $constants) {
        . ([scriptblock]::Create($statement.Extent.Text))
    }
}
$functions = @($collectorAst.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true))
foreach ($definition in $functions) { . ([scriptblock]::Create($definition.Extent.Text)) }
Assert-Check ($functions.Count -ge 12) 'expected collector functions loaded without main'
$originalPid = $PID
$family = Get-UsbFamily 'USB\VID_1A86&PID_7523\RAW_SERIAL_CANARY'
Assert-Check ($family.vid -eq '1A86' -and $family.pid -eq '7523' -and $family.ch340) 'CH340 family parsed without readonly PID collision'
Assert-Check ($PID -eq $originalPid) 'PowerShell automatic PID remains unchanged'
Assert-Check ((Get-UsbFamily 'USB\VID_1a86&PID_5523\OTHER').ch340) 'other supported CH340 PID'
Assert-Check (-not (Get-UsbFamily 'BTHENUM\PRIVATE_DEVICE').ch340) 'non-USB family not invented'
Assert-Check ($null -eq (Get-UsbFamily 'BTHENUM\PRIVATE_DEVICE').vid) 'unknown VID stays null'
Assert-Check ((Get-SafeNumber '43' 65535) -eq 43) 'numeric problem code preserved'
Assert-Check ($null -eq (Get-SafeNumber -1 65535)) 'negative code rejected'
Assert-Check ($null -eq (Get-SafeNumber 65536 65535)) 'overflow code rejected'
Assert-Check ($null -eq (Get-SafeNumber $true 65535)) 'boolean is not numeric status'
Assert-Check ($null -eq (Get-SafeNumber 'RAW_CREDENTIAL_CANARY' 65535)) 'free text is not numeric status'
$hash = Get-StableDeviceHash 'USB\VID_1A86&PID_7523\RAW_SERIAL_CANARY'
Assert-Check ($hash -match '^[a-f0-9]{64}$') 'SHA256 hex device ID'
Assert-Check ($hash -eq (Get-StableDeviceHash 'usb\vid_1a86&pid_7523\raw_serial_canary')) 'instance hashes stable across case'
Assert-Check ($hash -ne (Get-StableDeviceHash 'USB\VID_1A86&PID_7523\OTHER_SERIAL')) 'different IDs have different hashes'
Assert-Check ($null -eq (Get-StableDeviceHash '  ')) 'missing identifier remains absent'

$script:Canaries = @('RAW_SERIAL_CANARY', 'PRIVATE_USERNAME_CANARY', 'RAW_CREDENTIAL_CANARY', 'PRIVATE_MEMBER_CANARY', 'PRIVATE_GYM_CANARY', 'PRIVATE_MAC_CANARY', 'PRIVATE_SID_CANARY')
function Assert-NoPrivateData($Value, [string]$Label) {
    $serialized = ConvertTo-Json -InputObject $Value -Depth 16
    foreach ($canary in $script:Canaries) {
        Assert-Check (-not $serialized.Contains($canary)) ($Label + ': ' + $canary)
    }
}
$script:QaFolder = Join-Path ([System.IO.Path]::GetTempPath()) ('atlantic-usb-qa-' + [Guid]::NewGuid().ToString('N'))
[void][System.IO.Directory]::CreateDirectory($script:QaFolder)
try {
    # Linux-only fixture override: real Windows drive/reparse APIs are not
    # claimed validated. Scope every file operation to this fresh test folder.
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        function Get-LocalFilePath([string]$Path) {
            $full = [System.IO.Path]::GetFullPath($Path)
            if (-not $full.StartsWith($script:QaFolder + [System.IO.Path]::DirectorySeparatorChar)) { throw 'QA_PATH_OUTSIDE_TEMP' }
            return $full
        }
    }
    $logPath = Join-Path $script:QaFolder 'puerta.log'
    $safeLog = [ordered]@{
        event='relay_close_timeout'; at='2026-10-15T10:00:00-05:00'; port='COM7'; stage='serial_close'
        error_type='TimeoutError'; winerror=5; errno=13; command='a00100a1'; reason='shutdown'
        state='Desconocido; cierre USB pendiente'; member_id='PRIVATE_MEMBER_CANARY'; gym_id='PRIVATE_GYM_CANARY'
        error='RAW_CREDENTIAL_CANARY C:\Users\PRIVATE_USERNAME_CANARY'; serial='RAW_SERIAL_CANARY'
        settings=[ordered]@{password='RAW_CREDENTIAL_CANARY'}
    }
    $hostileLog = [ordered]@{
        event='relay_error'; at='PRIVATE_USERNAME_CANARY'; port='COM7 PRIVATE_USERNAME_CANARY'
        stage='PRIVATE_USERNAME_CANARY'; error_type='RAW_CREDENTIAL_CANARY'; errno=-1; winerror=70000
        command='RAW_CREDENTIAL_CANARY'; reason='PRIVATE_USERNAME_CANARY'; state='RAW_SERIAL_CANARY'
        error='RAW_CREDENTIAL_CANARY'; member_id='PRIVATE_MEMBER_CANARY'
    }
    $logLines = @((ConvertTo-Json -InputObject $safeLog -Compress -Depth 4), (ConvertTo-Json -InputObject $hostileLog -Compress), '{"event":"PRIVATE_USERNAME_CANARY","password":"RAW_CREDENTIAL_CANARY"}', 'PRIVATE_USERNAME_CANARY legacy plain text')
    [System.IO.File]::WriteAllLines($logPath, [string[]]$logLines, $script:Utf8)
    $sanitized = Get-SanitizedDoorLog $logPath
    Assert-Check ($sanitized.status -eq 'ok') 'door log read successfully'
    Assert-Check (@($sanitized.events).Count -eq 2 -and $sanitized.discarded_lines -eq 2) 'log allowlist and malformed lines handled'
    Assert-Check ($sanitized.events[0].winerror -eq 5 -and $sanitized.events[0].stage -eq 'serial_close') 'technical failure preserved'
    Assert-Check ($sanitized.events[0].at_utc -eq '2026-10-15T15:00:00.0000000Z') 'door instant normalized to UTC'
    Assert-Check (@($sanitized.events[1].PSObject.Properties).Count -eq 1) 'invalid technical values discarded'
    Assert-NoPrivateData $sanitized 'door log privacy'
    Assert-Check ((Get-SanitizedDoorLog (Join-Path $script:QaFolder 'absent.log')).status -eq 'not_found') 'missing log is nonfatal'

    $script:MockDevices = @(
        [pscustomobject]@{PNPDeviceID='USB\VID_1A86&PID_7523\RAW_SERIAL_CANARY';PNPClass='Ports';Name='PRIVATE_USERNAME_CANARY (COM7)';Status='OK';Present=$true;ConfigManagerErrorCode=0;Service='CH341SER';Manufacturer='PRIVATE_USERNAME_CANARY'},
        [pscustomobject]@{PNPDeviceID='BTHENUM\PRIVATE_MAC_CANARY';PNPClass='Bluetooth';Name='PRIVATE_USERNAME_CANARY';Status='Error';Present=$true;ConfigManagerErrorCode=43;Service='BTHUSB'},
        [pscustomobject]@{PNPDeviceID='SWD\MMDEVAPI\RAW_SERIAL_CANARY';PNPClass='AudioEndpoint';FriendlyName='PRIVATE_USERNAME_CANARY';Status='OK';Present=$true;ConfigManagerErrorCode=0;Service='C:\Users\PRIVATE_USERNAME_CANARY'},
        [pscustomobject]@{PNPDeviceID='SCSI\DISK\RAW_SERIAL_CANARY';PNPClass='DiskDrive';Name='PRIVATE_USERNAME_CANARY';Status='OK'}
    )
    $script:FailCim, $script:FailProperties = $false, $false
    function Get-CimInstance {
        [CmdletBinding()]param([string]$ClassName)
        if ($script:FailCim) { throw 'RAW_CREDENTIAL_CANARY' }
        if ($ClassName -eq 'Win32_OperatingSystem') { return [pscustomobject]@{Version='10.0.19045';BuildNumber='19045';SerialNumber='RAW_SERIAL_CANARY';RegisteredUser='PRIVATE_USERNAME_CANARY'} }
        return $script:MockDevices
    }
    function Get-PnpDeviceProperty {
        [CmdletBinding()]param([string]$InstanceId, [string[]]$KeyName)
        if ($script:FailProperties) { throw 'RAW_CREDENTIAL_CANARY' }
        $device = @($script:MockDevices | Where-Object {$_.PNPDeviceID -eq $InstanceId})[0]
        return @(
            [pscustomobject]@{KeyName='DEVPKEY_Device_Parent';Data='USB\ROOT_HUB30\RAW_SERIAL_CANARY'},
            [pscustomobject]@{KeyName='DEVPKEY_Device_ProblemCode';Data=(Read-Field $device 'ConfigManagerErrorCode')},
            [pscustomobject]@{KeyName='DEVPKEY_Device_DriverVersion';Data='3.8.2023.2'}
        )
    }
    function Get-WmiObject { [CmdletBinding()]param([string]$Class); throw 'RAW_CREDENTIAL_CANARY' }
    function Get-PnpDevice { [CmdletBinding()]param(); throw 'RAW_CREDENTIAL_CANARY' }
    $before = Get-PnpSnapshot
    Assert-Check ($before.status -eq 'ok' -and @($before.devices).Count -eq 3) 'mock PnP filters only relevant devices'
    $relay = @($before.devices | Where-Object {$_.ch340})[0]
    Assert-Check ($relay.device_hash -eq $hash -and $relay.com_port -eq 'COM7') 'CH340 hash and only COM extracted from name'
    Assert-Check ($relay.parent_hash -match '^[a-f0-9]{64}$') 'parent instance is hashed'
    Assert-Check (@($before.devices | Where-Object {$_.class -eq 'Bluetooth'})[0].problem_code -eq 43) 'Bluetooth problem code preserved'
    Assert-Check ($null -eq @($before.devices | Where-Object {$_.class -eq 'AudioEndpoint'})[0].service) 'path-shaped service value rejected'
    Assert-NoPrivateData $before 'PnP snapshot privacy'
    $script:MockDevices[0].Status='Error';$script:MockDevices[0].Present=$false;$script:MockDevices[0].ConfigManagerErrorCode=24
    $script:MockDevices = @($script:MockDevices[0], $script:MockDevices[2], [pscustomobject]@{PNPDeviceID='USB\VID_1234&PID_ABCD\RAW_SERIAL_CANARY_NEW';PNPClass='USB';Status='OK';Present=$true;ConfigManagerErrorCode=0;Service='usbccgp'})
    $after = Get-PnpSnapshot
    $delta = Compare-PnpSnapshots $before $after
    Assert-Check ($delta.comparison_available -and @($delta.added).Count -eq 1 -and @($delta.removed).Count -eq 1 -and @($delta.changed).Count -eq 1) 'actual before/after differences detected'
    Assert-Check ('problem_code' -in $delta.changed[0].fields -and 'present' -in $delta.changed[0].fields) 'changed fields identified'
    $unavailable = [pscustomobject]@{status='unavailable';devices=@()}
    foreach ($pair in @(@($before,$unavailable), @($unavailable,$after))) {
        $incomplete = Compare-PnpSnapshots $pair[0] $pair[1]
        Assert-Check (-not $incomplete.comparison_available -and @($incomplete.added).Count -eq 0 -and @($incomplete.removed).Count -eq 0 -and @($incomplete.changed).Count -eq 0) 'unavailable snapshot cannot invent device disappearance'
    }
    $script:FailProperties = $true
    $limited = Get-PnpSnapshot
    Assert-Check ($limited.status -eq 'ok' -and $limited.property_query_failures -eq 3) 'optional property errors degrade without stopping inventory'
    Assert-NoPrivateData $limited 'PnP property failure privacy'
    $script:FailCim = $true
    $failed = Get-PnpSnapshot
    Assert-Check ($failed.status -eq 'unavailable' -and @($failed.devices).Count -eq 0) 'all unavailable PnP APIs fail gracefully'
    Assert-NoPrivateData $failed 'PnP source failure privacy'
    $script:FailCim, $script:FailProperties = $false, $false
    $metadata = Get-SystemMetadata
    Assert-Check ($metadata.os_version -eq '10.0.19045' -and $metadata.collector_process_bits -in @(32,64)) 'OS/process metadata uses permitted fields'
    Assert-NoPrivateData $metadata 'OS metadata privacy'

    $eventXml = '<Event><System><Security UserID="PRIVATE_SID_CANARY"/></System><EventData><Data Name="DeviceInstanceId">USB\VID_1A86&amp;PID_7523\RAW_SERIAL_CANARY</Data><Data Name="Status">0xC0000001</Data><Data Name="ProblemCode">43</Data><Data Name="ReasonCode">PRIVATE_USERNAME_CANARY</Data><Data Name="UserName">PRIVATE_USERNAME_CANARY</Data><Data Name="Message">RAW_CREDENTIAL_CANARY</Data></EventData></Event>'
    $eventRecord = [pscustomobject]@{ProviderName='BTHUSB';TimeCreated=[DateTime]::UtcNow;Id=17;Level=2;RecordId=1234;Task=0;Opcode=0;XmlFixture=$eventXml}
    $eventRecord | Add-Member -MemberType ScriptMethod -Name ToXml -Value { return $this.XmlFixture }
    $eventRecord | Add-Member -MemberType ScriptProperty -Name Message -Value { throw 'RAW_MESSAGE_MUST_NOT_BE_READ' }
    $unknownProvider = [pscustomobject]@{ProviderName='Microsoft-Windows-Bluetooth-PRIVATE_USERNAME_CANARY';TimeCreated=[DateTime]::UtcNow;Id=18;Level=2;RecordId=1235;Task=0;Opcode=0;XmlFixture=$eventXml}
    $unknownProvider | Add-Member -MemberType ScriptMethod -Name ToXml -Value { return $this.XmlFixture }
    $script:FailEvents = $false
    $script:MockEvents = @($eventRecord,$unknownProvider)
    function Get-WinEvent {
        [CmdletBinding()]param([hashtable]$FilterHashtable,[int]$MaxEvents)
        if ($script:FailEvents) { throw 'RAW_CREDENTIAL_CANARY' }
        Assert-Check ($FilterHashtable.LogName -eq 'System' -and $MaxEvents -eq 3000) 'event API bounded System-only read'
        $age = ([DateTime]::Now - $FilterHashtable.StartTime).TotalMinutes
        Assert-Check ($age -ge 19.9 -and $age -le 20.1) 'event window is twenty minutes'
        return $script:MockEvents
    }
    $events = Get-SystemUsbEvents
    Assert-Check ($events.status -eq 'ok' -and @($events.events).Count -eq 2) 'System event fixtures collected without reading Message'
    Assert-Check ($events.events[0].status_fields.Status -eq '0xC0000001' -and $events.events[0].devices[0].device_hash -eq $hash) 'numeric status and hashed event instance preserved'
    Assert-Check ($events.events[1].provider -eq 'OtherUSBorBluetoothProvider') 'unknown provider text cannot leak username'
    Assert-NoPrivateData $events 'System event privacy'
    $script:FailEvents = $true
    Assert-Check ((Get-SystemUsbEvents).status -eq 'unavailable') 'event permission/API failure is nonfatal'
    Assert-NoPrivateData $script:Warnings.ToArray() 'warning privacy'
    Save-TechnicalJson $script:QaFolder 'safe.json' $sanitized
    $roundtrip = ConvertFrom-Json ([System.IO.File]::ReadAllText((Join-Path $script:QaFolder 'safe.json')))
    Assert-Check (@($roundtrip.events).Count -eq 2) 'technical JSON roundtrip keeps array shape'
    Assert-NoPrivateData $roundtrip 'serialized artifact privacy'
    Write-Host ('PASS: ' + $script:CheckCount + ' PowerShell helper/mock/privacy checks. Linux PowerShell only; no Windows/PnP/hardware claim.')
} finally {
    [System.IO.Directory]::Delete($script:QaFolder, $true)
}
