# collect-veeam.ps1 — снять полную картину бэкапов Veeam в CSV/TXT
# Запуск: PowerShell (Administrator) на Veeam-сервере 192.168.160.14
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   & 'C:\veeam-audit\collect-veeam.ps1'
# Результат: C:\veeam-audit\*.csv|txt  -> скопировать себе

$Out = 'C:\veeam-audit'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$ProgressPreference = 'SilentlyContinue'
$ErrorActionPreference = 'Continue'
$ErrFile = "$Out\99-errors.txt"
if (Test-Path $ErrFile) { Remove-Item $ErrFile }

function Save-Csv($obj, $name) {
  try {
    if ($null -eq $obj) { "EMPTY: $name" | Out-File $ErrFile -Append -Encoding UTF8; return }
    @($obj) | Export-Csv "$Out\$name" -NoTypeInformation -Encoding UTF8
  } catch { "FAILED ${name}: $($_.Exception.Message)" | Out-File $ErrFile -Append -Encoding UTF8 }
}
function Save-Txt($text, $name) {
  try { $text | Out-File "$Out\$name" -Encoding UTF8 }
  catch { "FAILED ${name}: $($_.Exception.Message)" | Out-File $ErrFile -Append -Encoding UTF8 }
}
function Try-Cmd([scriptblock]$sb, $fallback) {
  try { & $sb } catch { $fallback }
}

# --------------------------------------------------- 0a. подключение модуля Veeam
# Veeam 12+  -> Veeam.Backup.PowerShell ;  Veeam 9/10/11 -> VeeamBackup
$mod = $null
foreach ($p in @('C:\Program Files\Veeam\Backup\PowerShell','C:\Program Files\Veeam\Backup\PowerShell\Modules')) {
  if ((Test-Path $p) -and ($env:PSModulePath -notlike "*$p*")) { $env:PSModulePath += ";$p" }
}
foreach ($m in @('Veeam.Backup.PowerShell','VeeamBackup')) {
  try { Import-Module $m -EA Stop; $mod = $m; break } catch {}
}
if (-not $mod) {
  $psd = Get-ChildItem 'C:\Program Files\Veeam' -Recurse -Depth 5 -Filter 'Veeam*.psd1' -EA SilentlyContinue |
         Where-Object { $_.BaseName -match 'Backup' } | Select-Object -First 1
  if ($psd) {
    $env:PSModulePath += ';' + $psd.Directory.Parent.FullName
    try { Import-Module $psd.BaseName -EA Stop; $mod = $psd.BaseName } catch { "autoload $($psd.BaseName): $($_.Exception.Message)" | Out-File $ErrFile -Append -Encoding UTF8 }
  }
}
if (-not $mod) { "MODULE NOT FOUND (ни Veeam.Backup.PowerShell, ни VeeamBackup)" | Out-File $ErrFile -Append -Encoding UTF8 }

# ---------------------------------------------------------------- 0. сервер
Save-Txt @"
COLLECTED : $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss K')
COMPUTER  : $env:COMPUTERNAME
MODULE    : $mod
VEEAM VER : $(Try-Cmd { (Get-Module $mod).Version.ToString() } 'n/a')
CONNECTED : $(Try-Cmd { (Connect-VeeamServer).Name } 'not connected')
"@ '00-server.txt'

if ($mod) { try { $null = Connect-VeeamServer -EA SilentlyContinue } catch { "connect: $($_.Exception.Message)" | Out-File $ErrFile -Append -Encoding UTF8 } }

# какие cmdlet вообще есть (помогает, если что-то не отработало)
Save-Csv (Try-Cmd { Get-Command -Module $mod } 'n/a') '90-available-cmdlets.csv'

# ---------------------------------------------------------------- 1. джобы
$jobs = Try-Cmd { Get-VBRJob } (Try-Cmd { Get-VeeamJob | Where-Object { $_.JobType -match 'Job|Schedule|Task' } } 'n/a')
Save-Csv ($jobs | Select-Object * ) '01-jobs.csv'
Save-Txt ($jobs | Format-List * | Out-String -Width 300) '02-jobs-readable.txt'

$jobsHi = Try-Cmd { Get-VeeamJob | Where-Object { $_.JobType -in 'BackupJob','BackupSchedule','BackupTask' } } 'n/a'
Save-Txt ($jobsHi | Select-Object Name, JobType, Enabled, ScheduleEnabled,
         @{n='Mode';e={$_.BackupMode}}, @{n='NextRun';e={$_.NextRun}},
         @{n='LastRun';e={$_.LastRun}}, @{n='Repos';e={($_.Repository -join ';')}} |
         Format-Table -AutoSize | Out-String -Width 300) '01b-jobs-summary.txt'

# ---------------------------------------------------------------- 2. хранилища
Save-Csv (Try-Cmd { Get-VBRRepository | Select-Object * } 'n/a') '03-repositories.csv'
Save-Txt (Try-Cmd { Get-VBRRepository |
         Select-Object Name, Type, Path, CapacityGB, FreeSpaceGB, @{n='UsedGB';e={[math]::Round(($_.CapacityGB-$_.FreeSpaceGB),1)}},
         @{n='MaxPoints';e={$_.MaximumBackupPoints}}, EnableImmediateIntegrityCheck, StorageOptions |
         Format-List * | Out-String -Width 300 } 'n/a') '03b-repositories-readable.txt'
Save-Csv (Try-Cmd { Get-VBRStorageOptions } 'n/a') '03c-repository-storage-options.csv'

# ---------------------------------------------------------------- 3. прокси
Save-Csv (Try-Cmd { Get-VBRProxy | Select-Object * } 'n/a') '04-proxies.csv'
Save-Txt (Try-Cmd { Get-VBRProxy |
         Select-Object Name, HostName, TransportMode, @{n='MaxTasks';e={$_.MaxTasks}}, Description |
         Format-Table -AutoSize | Out-String -Width 300 } 'n/a') '04b-proxies-readable.txt'

# ---------------------------------------------------------------- 4. инвентарь (что вообще есть в Veeam)
Save-Csv (Try-Cmd { Get-VBRComputer | Select-Object Name, Type, @{n='Host';e={$_.Host}}, @{n='VMCount';e={$_.VmObjects.Count}} } 'n/a') '05-inventory.csv'

# ---------------------------------------------------------------- 5. сессии
$sessions = Try-Cmd { Get-VBRJobSession | Where-Object { $_.CreationTime -gt (Get-Date).AddDays(-60) } } 'n/a'
Save-Csv ($sessions | ForEach-Object {
    [pscustomobject]@{
      Job      = $_.JobName
      Status   = $_.Status
      Start    = $_.CreationTime
      End      = $_.EndTime
      VMs      = $_.VmObjects.Count
      TotalGB  = [math]::Round((($_.VmObjects | Measure-Object TotalSize -Sum).Sum)/1GB,2)
      TransGB  = [math]::Round($_.TotalTransferredBytes/1GB,2)
      Warnings = ($_.Warnings -join '; ')
    } } | Sort-Object Start -Descending) '06-sessions-last.csv'

# ---------------------------------------------------------------- 6. покрытие ВМ <-> джоб
# берём последнюю успешную сессию каждого джоба
$cov = foreach ($jname in ($sessions | Where-Object Status -eq 'Success' | Select-Object -ExpandProperty JobName -Unique)) {
  $last = $sessions | Where-Object { $_.JobName -eq $jname -and $_.Status -eq 'Success' } |
          Sort-Object CreationTime -Descending | Select-Object -First 1
  foreach ($vm in $last.VmObjects) {
    [pscustomobject]@{
      Job      = $jname
      VM       = $vm.Name
      Status   = $vm.Status
      SizeGB   = [math]::Round($vm.TotalSize/1GB,2)
      Restored = $vm.IsEnabled
      Session  = $last.CreationTime
    }
  }
}
Save-Csv $cov '07-vm-coverage.csv'
Save-Txt ($cov | Group-Object VM | Select-Object Name, Count |
         Sort-Object Name | Format-Table -AutoSize | Out-String -Width 200) '07b-vm-uniq.txt'

# ---------------------------------------------------------------- 7. исключения + опции по джобам
$excl = foreach ($job in @($jobs)) {
  $name = $job.Name
  "===================== JOB: $name ($($job.JobType)) ====================="
  "--- properties ---"
  ($job | Get-Member -MemberType Properties | Select-Object -ExpandProperty Name) -join ', '
  foreach ($p in 'Enabled','ScheduleEnabled','Mode','BackupMode','ScheduleInfo','Schedule','Type','Id') {
    if ($job.PSObject.Properties[$p]) { "[$p] " + (($job.$p | Out-String -Width 300)) }
  }
  "--- options ---"
  $o = $null
  try { $o = $job.GetOptions() } catch { $o = Try-Cmd { Get-VBRJobOption -Job $job } $null }
  if ($o) {
    if ($o.Options) { $o.Options | Format-List * | Out-String -Width 300 }
    "--- EXCLUDED VMs ---"
    if ($o.Options.VmExclusionSettings) { $o.Options.VmExclusionSettings | Select-Object Name, Id | Format-Table -AutoSize | Out-String -Width 200 }
    else { 'нет данных (проверить вкладку VM Exclusions в консоли)' }
  } else { 'опции не прочитались — смотри консоль: Edit Job -> VM Exclusions' }
  ""
}
Save-Txt $excl '08-exclusions.txt'

# ---------------------------------------------------------------- 8. лицензия
Save-Txt (Try-Cmd { Get-VBRLicense | Format-List * | Out-String -Width 300 } 'n/a') '09-license.txt'

Write-Host ''
Write-Host 'Готово. Файлы в:' $Out
Get-ChildItem $Out | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize