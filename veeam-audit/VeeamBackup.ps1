<#
    Veeam — сырой отчёт без Excel.
    Создаёт папку VeeamDump_ГГГГ-ММ-ДД_ЧЧ-мм рядом со скриптом
    с CSV-файлами и одним сводным TXT.
#>

# ---------- НАСТРОЙКИ ----------
$ErrorActionPreference = 'Continue'
$ScriptDir   = 'C:\Users\Администратор\Desktop\ps1'
$Stamp       = Get-Date -Format 'yyyy-MM-dd_HH-mm'
$OutDir      = Join-Path $ScriptDir "VeeamDump_$Stamp"
$VeeamServer = 'localhost'

New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
Write-Host "Папка вывода: $OutDir" -ForegroundColor Cyan

# ---------- ПОДКЛЮЧЕНИЕ ----------
Import-Module Veeam.Backup.PowerShell
Connect-VBRServer -Server $VeeamServer | Out-Null

# ---------- ХЕЛПЕР ----------
function Save-Csv($data, $name) {
    $path = Join-Path $OutDir "$name.csv"
    if ($data) {
        $data | Export-Csv -Path $path -NoTypeInformation -Encoding UTF8
    } else {
        "(пусто)" | Out-File -FilePath $path -Encoding UTF8
    }
    Write-Host "  -> $name.csv" -ForegroundColor DarkGray
}

# ============================================================
# 1. СЕРВЕРЫ
# ============================================================
Write-Host "Сбор: серверы..." -ForegroundColor Cyan
$Servers = @()
foreach ($s in (Get-VBRServer)) {
    $Servers += [PSCustomObject]@{
        Name = "$($s.Name)"
        Type = "$($s.Type)"
        Id   = "$($s.Id)"
    }
}
Save-Csv $Servers '01-Servers'

# ============================================================
# 2. ЛИЦЕНЗИЯ
# ============================================================
Write-Host "Сбор: лицензия..." -ForegroundColor Cyan
$License = @()
try {
    $lic = Get-VBRInstalledLicense
    $License += [PSCustomObject]@{
        Status         = "$($lic.Status)"
        ExpirationDate = "$($lic.ExpirationDate)"
        Type           = "$($lic.Type)"
        Edition        = "$($lic.Edition)"
        LicensedTo     = "$($lic.LicensedTo)"
    }
} catch {
    $License += [PSCustomObject]@{ Error = "$($_.Exception.Message)" }
}
Save-Csv $License '02-License'

# ============================================================
# 3. ЗАДАНИЯ — главное
# ============================================================
Write-Host "Сбор: задания..." -ForegroundColor Cyan
$Jobs = @()
foreach ($j in (Get-VBRJob)) {
    Write-Host "  задание: $($j.Name)" -ForegroundColor DarkGray

    # Расписание. Время старта берём несколькими путями: свойство .Time у CSchedule* в разных
    # версиях Veeam заполнено по-разному, поэтому проверяем варианты и берём первый непустой.
    $schedule = ''; $schedTime = ''
    function Get-SchedTime($o) {
        if (-not $o) { return '' }
        foreach ($p in @('Time','DailyHours','Hours','StartTime','TimeOfDay')) {
            $v = $null
            try { $v = $o.$p } catch {}
            if ($null -eq $v) { continue }
            if ($v -is [datetime]) { return $v.ToString('HH:mm') }
            $t = "$v"
            if ($t -match '^\s*(\d{1,2}):(\d{2})') { return "$($Matches[1].PadLeft(2,'0')):$($Matches[2])" }
            if ($t -match '^\s*(\d{1,2})(\d{2})\s*$' -and $Matches[1] -le 23 -and $Matches[2] -le 59) {
                return "$($Matches[1].PadLeft(2,'0')):$($Matches[2])"
            }
            if ($t -match 'Time\s*=\s*(\d{1,2}:\d{2})') { return $Matches[1] }
        }
        return ''
    }
    try {
        $opts = $j.GetScheduleOptions()
        $sched = $null
        foreach ($path in @($opts, $opts.Options, $opts.Options.Schedule, $opts.Schedule)) {
            if (-not $path) { continue }
            foreach ($n in @('OptionsDaily','DailyOptions','Daily')) {
                $d = $null; try { $d = $path.$n } catch {}
                if ($d -and $d.Enabled) { $sched = @{ kind = 'daily'; obj = $d }; break }
            }
            if ($sched) { break }
        }
        if ($sched) {
            $schedTime = Get-SchedTime $sched.obj
            $schedule  = "Ежедневно в $schedTime"
        }
        elseif ($opts.OptionsPeriodically -and $opts.OptionsPeriodically.Enabled) {
            $schedule = "Каждые $($opts.OptionsPeriodically.Frequency) $($opts.OptionsPeriodically.FrequencyType)"
            $schedTime = Get-SchedTime $opts.OptionsPeriodically
        }
        elseif ($opts.OptionsMonthly -and $opts.OptionsMonthly.Enabled) {
            $schedTime = Get-SchedTime $opts.OptionsMonthly
            $schedule = "Ежемесячно день $($opts.OptionsMonthly.DayOfMonth) в $schedTime"
        }
        elseif ($opts.OptionsContinuous -and $opts.OptionsContinuous.Enabled) {
            $schedule = "Непрерывно"
        }
        else {
            $schedule = "(включено=$($j.IsScheduleEnabled))"
        }
        if ($schedTime -eq '') {
            # если время так и не нашли — покажем фактическое время старта из последних сессий
            try {
                $ls = Get-VBRJobSession | Where-Object { $_.JobName -eq $j.Name } |
                      Sort-Object CreationTime -Descending | Select-Object -First 5
                if ($ls) {
                    $times = $ls | ForEach-Object { ([datetime]$_.CreationTime).ToString('HH:mm') } |
                              Select-Object -Unique
                    $schedule += " [фактически по последним запускам: " + ($times -join ', ') + "]"
                }
            } catch {}
        }
    } catch { $schedule = "ошибка: $($_.Exception.Message)" }

    # Репозиторий
    $target = ''
    try {
        $st = $j.GetTargetStorages()
        if ($st) {
            $names = @()
            foreach ($x in $st) { if ($x.Name) { $names += $x.Name } }
            $target = $names -join '; '
        }
    } catch { $target = "ошибка: $($_.Exception.Message)" }

    # Объекты
    $objs = @()
    try {
        $o = $j.GetObjectsInJob()
        if ($o) { foreach ($x in $o) { if ($x.Name) { $objs += $x.Name } } }
    } catch {}
    $objList = if ($objs.Count) { $objs -join '; ' } else { '(пусто)' }

    # Последний/следующий запуск
    $lastRun = ''; $nextRun = ''; $lastRes = ''
    try { $lastRun = "$($j.GetLastRun())"    } catch {}
    try { $nextRun = "$($j.GetNextRun())"    } catch {}
    try { $lastRes = "$($j.GetLastResult())" } catch {}

    # Опции хранения
    $retain = ''
    try {
        $o = $j.GetOptions()
        if ($o -and $o.BackupStorageOptions -and $o.BackupStorageOptions.RetainDays) {
            $retain = "$($o.BackupStorageOptions.RetainDays)"
        }
    } catch {}

    $Jobs += [PSCustomObject]@{
        'Задание'            = "$($j.Name)"
        'Тип'                = "$($j.JobType)"
        'Включено'           = "$($j.IsScheduleEnabled)"
        'Расписание'         = $schedule
        'Время запуска'      = $schedTime
        'Последний запуск'   = $lastRun
        'Следующий запуск'   = $nextRun
        'Последний результат'= $lastRes
        'Объектов'           = $objs.Count
        'Что бэкапит'        = $objList
        'Куда (репозиторий)' = $target
        'Хранение (дней)'    = $retain
        'Описание'           = "$($j.Description)"
    }
}
Save-Csv $Jobs '03-Jobs'

# ============================================================
# 4. РЕПОЗИТОРИИ
# ============================================================
Write-Host "Сбор: репозитории..." -ForegroundColor Cyan
$Repos = @()
foreach ($r in (Get-VBRBackupRepository)) {
    $cap = ''; $free = ''
    try {
        $cap  = "$($r.GetContainer().CachedTotalSpace.InGigabytes)"
        $free = "$($r.GetContainer().CachedFreeSpace.InGigabytes)"
    } catch {}

    $Repos += [PSCustomObject]@{
        'Репозиторий'   = "$($r.Name)"
        'Тип'           = "$($r.Type)"
        'Путь'          = "$($r.Path)"
        'Объём (ГБ)'    = $cap
        'Свободно (ГБ)' = $free
    }
}
Save-Csv $Repos '04-Repositories'

# ============================================================
# 5. ПРОКСИ
# ============================================================
Write-Host "Сбор: прокси..." -ForegroundColor Cyan
$Proxies = @()
try {
    foreach ($p in (Get-VBRViProxy)) {
        $Proxies += [PSCustomObject]@{
            Name = "$($p.Name)"; Type = "$($p.Type)"; Host = "$($p.Host.Name)"
        }
    }
} catch {}
try {
    foreach ($p in (Get-VBRHvProxy)) {
        $Proxies += [PSCustomObject]@{
            Name = "$($p.Name)"; Type = "$($p.Type)"; Host = "$($p.Host.Name)"
        }
    }
} catch {}
Save-Csv $Proxies '05-Proxies'

# ============================================================
# 6. СЕССИИ — что делалось и когда
# ============================================================
Write-Host "Сбор: сессии..." -ForegroundColor Cyan
$Sessions = @()
try {
    $all = Get-VBRBackupSession | Sort-Object CreationTime -Descending | Select-Object -First 500
    foreach ($s in $all) {
        $dur = ''
        try { if ($s.EndTime) { $dur = "$([math]::Round(($s.EndTime - $s.CreationTime).TotalMinutes,1))" } } catch {}

        $Sessions += [PSCustomObject]@{
            'Время'        = "$($s.CreationTime)"
            'Задание'      = "$($s.JobName)"
            'Результат'    = "$($s.Result)"
            'Состояние'    = "$($s.State)"
            'Окончание'    = "$($s.EndTime)"
            'Длит. (мин)'  = $dur
        }
    }
} catch {
    $Sessions += [PSCustomObject]@{ Error = "$($_.Exception.Message)" }
}
Save-Csv $Sessions '06-Sessions'

# ============================================================
# 7. ТОЧКИ ВОССТАНОВЛЕНИЯ — что реально создано
# ============================================================
Write-Host "Сбор: точки восстановления..." -ForegroundColor Cyan
$RestorePoints = @()
try {
    foreach ($rp in (Get-VBRRestorePoint | Sort-Object CreationTime -Descending)) {
        $RestorePoints += [PSCustomObject]@{
            'Время создания' = "$($rp.CreationTime)"
            'ВМ / объект'    = "$($rp.VMName)"
            'Имя точки'      = "$($rp.Name)"
            'Тип'            = "$($rp.Type)"
        }
    }
} catch {
    $RestorePoints += [PSCustomObject]@{ Error = "$($_.Exception.Message)" }
}
Save-Csv $RestorePoints '07-RestorePoints'

# ============================================================
# 8. СВОДКА ПО ЗАДАНИЯМ — успех/ошибка
# ============================================================
Write-Host "Сбор: сводка..." -ForegroundColor Cyan
$JobStats = @()
foreach ($j in (Get-VBRJob)) {
    $sess = @()
    try { $sess = @(Get-VBRBackupSession | Where-Object { $_.JobName -eq $j.Name }) } catch {}
    $total = $sess.Count
    $ok    = @($sess | Where-Object Result -eq 'Success').Count
    $warn  = @($sess | Where-Object Result -eq 'Warning').Count
    $fail  = @($sess | Where-Object Result -eq 'Failed').Count

    $JobStats += [PSCustomObject]@{
        'Задание'      = "$($j.Name)"
        'Всего сессий' = $total
        'Успешно'      = $ok
        'Предупрежд.'  = $warn
        'Ошибок'       = $fail
    }
}
Save-Csv $JobStats '08-JobStats'

# ============================================================
# 9. РАЗМЕРЫ БЭКАПОВ
# ============================================================
Write-Host "Сбор: размеры бэкапов..." -ForegroundColor Cyan
$BackupSizes = @()
try {
    foreach ($b in (Get-VBRBackup)) {
        $size = ''
        try { $size = "$([math]::Round($b.GetStorages().Stats.BackupSize / 1GB, 2))" } catch {}
        $BackupSizes += [PSCustomObject]@{
            'Имя бэкапа'  = "$($b.Name)"
            'Размер (ГБ)' = $size
        }
    }
} catch {
    $BackupSizes += [PSCustomObject]@{ Error = "$($_.Exception.Message)" }
}
Save-Csv $BackupSizes '09-BackupSizes'

# ============================================================
# 10. ОШИБКИ — тексты упавших заданий
# ============================================================
Write-Host "Сбор: ошибки..." -ForegroundColor Cyan
$FailDetails = @()
try {
    $failedSessions = Get-VBRBackupSession | Where-Object Result -eq 'Failed' |
        Sort-Object CreationTime -Descending | Select-Object -First 30
    foreach ($sess in $failedSessions) {
        $errs = @()
        try {
            $errs = @($sess.Logger.GetLog().UpdatedRecords |
                Where-Object Status -eq 'EFailed' |
                Select-Object -ExpandProperty Title)
        } catch {}
        if ($errs.Count -eq 0) { $errs = @('(без текста ошибки)') }
        foreach ($e in $errs) {
            $FailDetails += [PSCustomObject]@{
                'Время'   = "$($sess.CreationTime)"
                'Задание' = "$($sess.JobName)"
                'Ошибка'  = "$e"
            }
        }
    }
} catch {
    $FailDetails += [PSCustomObject]@{ Error = "$($_.Exception.Message)" }
}
Save-Csv $FailDetails '10-FailedErrors'

# ============================================================
# 11. ДИСКИ СЕРВЕРА
# ============================================================
Write-Host "Сбор: диски..." -ForegroundColor Cyan
$Drives = @()
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -or $_.Free } | ForEach-Object {
    $Drives += [PSCustomObject]@{
        'Диск'       = "$($_.Name):"
        'Занято ГБ'  = "$([math]::Round($_.Used/1GB,2))"
        'Свободно ГБ'= "$([math]::Round($_.Free/1GB,2))"
        'Всего ГБ'   = "$([math]::Round(($_.Used+$_.Free)/1GB,2))"
    }
}
Save-Csv $Drives '11-Disks'

# ============================================================
# СВОДНЫЙ TXT — самое главное в одном файле
# ============================================================
$summaryPath = Join-Path $OutDir '00-SUMMARY.txt'
$lines = @()
$lines += "=========================================="
$lines += " VEEAM ОТЧЁТ  ($Stamp)"
$lines += "=========================================="
$lines += ""
$lines += "--- ЛИЦЕНЗИЯ ---"
$License | Format-List | Out-String -Width 200 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- СЕРВЕРЫ ($($Servers.Count)) ---"
$Servers | Format-Table Name, Type -AutoSize | Out-String -Width 200 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- ЗАДАНИЯ ($($Jobs.Count)) ---"
$Jobs | Format-Table 'Задание','Тип','Включено','Расписание','Последний результат' -AutoSize |
    Out-String -Width 250 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- РЕПОЗИТОРИИ ($($Repos.Count)) ---"
$Repos | Format-Table -AutoSize | Out-String -Width 200 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- СЕССИИ (последние 50) ---"
$Sessions | Select-Object -First 50 | Format-Table -AutoSize |
    Out-String -Width 200 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- СВОДКА ---"
$JobStats | Format-Table -AutoSize | Out-String -Width 200 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- ОШИБКИ (последние 30) ---"
$FailDetails | Format-Table -AutoSize | Out-String -Width 250 | ForEach-Object { $lines += $_ }
$lines += ""
$lines += "--- ДИСКИ ---"
$Drives | Format-Table -AutoSize | Out-String -Width 200 | ForEach-Object { $lines += $_ }

$lines | Out-File -FilePath $summaryPath -Encoding UTF8

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " ГОТОВО: $OutDir" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Файлы:" -ForegroundColor Yellow
Get-ChildItem $OutDir | Select-Object Name, Length | Format-Table -AutoSize

Disconnect-VBRServer