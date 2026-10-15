# collect-vcenter-vms.ps1 — полный список ВМ vCenter (нужен, чтобы найти «не бэкапятся»)
# Запуск: PowerShell (Administrator) на Veeam-сервере или на любой машине с VMware.PowerCLI
#   Install-Module VMware.PowerCLI -Scope CurrentUser   (один раз)
#   & 'C:\veeam-audit\collect-vcenter-vms.ps1'
# Результат: C:\veeam-audit\10-vcenter-vms.csv

$Out = 'C:\veeam-audit'
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$vcenter = '192.168.160.202'

if (-not (Get-Module -ListAvailable VMware.PowerCLI)) {
  "PowerCLI не найден, пробуем поставить с PSGallery (нужен интернет)..." |
    Out-File "$Out\10-powercli-install.log" -Encoding UTF8
  try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    Install-Module VMware.PowerCLI -Scope CurrentUser -Force -AllowClobber -ErrorAction Stop
  } catch { "Install-Module: $($_.Exception.Message)" | Out-File "$Out\10-powercli-install.log" -Append -Encoding UTF8 }
}

try {
  Import-Module VMware.PowerCLI -ErrorAction Stop
} catch {
  "НЕТ VMware.PowerCLI. Запасной путь: vCenter Web Client -> Inventory -> Virtual Machines -> Actions -> Export List -> CSV, сохранить как 10-vcenter-vms.csv" |
    Out-File "$Out\10-powercli-install.log" -Append -Encoding UTF8
  Get-Content "$Out\10-powercli-install.log"; exit 1
}

Connect-VIServer -Server $vcenter -ErrorAction Stop | Out-Null

$raw = Get-VM -Server $vcenter

$raw | Select-Object Name,
    PowerState,
    @{n='GuestOS';e={$_.Guest.GuestFullName}},
    @{n='IPs';e={($_.Guest.IpAddress | Where-Object {$_}) -join ','}},
    @{n='ESXiHosts';e={($_.ExtensionData.Runtime.Host | Select-Object -ExpandProperty Name) -join ','}},
    @{n='Datastores';e={($_.ExtensionData.Runtime.Datastore | Select-Object -ExpandProperty Name) -join ','}},
    @{n='CPUs';e={$_.ExtensionData.Runtime.Hardware.Cpu.NumCpu}},
    @{n='RAM_GB';e={[math]::Round($_.ExtensionData.Runtime.Memory.SizeMB/1024,1)}} |
    Sort-Object Name |
    Export-Csv "$Out\10-vcenter-vms.csv" -NoTypeInformation -Encoding UTF8

# сводка по ESXi (полезно: сколько всего ВМ и где)
$raw | Group-Object { ($_.ExtensionData.Runtime.Host | Select-Object -First 1).Name } |
    Select-Object Name, Count | Format-Table -AutoSize |
    Out-File "$Out\11-vcenter-by-esxi.txt" -Encoding UTF8

# отдельный список выключенных/осиротевших — их нельзя бэкапить без чистки
$raw | Where-Object { $_.PowerState -ne 'PoweredOn' -or -not $_.ExtensionData.Runtime.Host } |
    Select-Object Name, PowerState | Export-Csv "$Out\12-vcenter-down-orphaned.csv" -NoTypeInformation -Encoding UTF8

Write-Host "OK: $($raw.Count) VM -> $Out\10-vcenter-vms.csv"
Disconnect-VIServer -Server $vcenter -Confirm:$false