<#
  Prava.uz - PostgreSQL zaxira nusxasi (Windows).

  Ishlatish (loyiha ildizidan):
      powershell -ExecutionPolicy Bypass -File tools\backup.ps1
      powershell -ExecutionPolicy Bypass -File tools\backup.ps1 -Keep 30

  - Ulanish ma'lumotlari .env dan o'qiladi (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT).
  - Parol faqat PGPASSWORD muhit o'zgaruvchisi orqali beriladi va hech qayerga chiqarilmaydi.
  - Natija: backups\prava_YYYYMMDD_HHMM.dump (pg_dump -F c, custom format).
  - Oxirgi $Keep ta nusxa saqlanadi, eskilari o'chiriladi.

  Kunlik ishga tushirish (Task Scheduler), masalan har kuni 03:00 da:
      schtasks /Create /SC DAILY /ST 03:00 /TN "PravaUzBackup" `
        /TR "powershell -ExecutionPolicy Bypass -File D:\projects\pravauz\tools\backup.ps1"
#>
param(
    [int]$Keep = 14
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"
$backupDir = Join-Path $root "backups"

# --- .env ni o'qish ---
if (-not (Test-Path $envFile)) { throw ".env topilmadi: $envFile" }
$cfg = @{}
foreach ($line in Get-Content $envFile -Encoding UTF8) {
    $t = $line.Trim()
    if ($t -eq "" -or $t.StartsWith("#") -or -not $t.Contains("=")) { continue }
    $k, $v = $t.Split("=", 2)
    $v = $v.Trim()
    if ($v.Length -ge 2 -and (($v.StartsWith('"') -and $v.EndsWith('"')) -or ($v.StartsWith("'") -and $v.EndsWith("'")))) {
        $v = $v.Substring(1, $v.Length - 2)
    }
    $cfg[$k.Trim()] = $v
}
if ($cfg["DB_ENGINE"] -and $cfg["DB_ENGINE"] -ne "postgres") {
    throw "DB_ENGINE=$($cfg['DB_ENGINE']) - zaxira skripti faqat PostgreSQL uchun."
}
$dbName = if ($cfg["DB_NAME"]) { $cfg["DB_NAME"] } else { "prava_uz" }
$dbUser = if ($cfg["DB_USER"]) { $cfg["DB_USER"] } else { "prava" }
$dbHost = if ($cfg["DB_HOST"]) { $cfg["DB_HOST"] } else { "localhost" }
$dbPort = if ($cfg["DB_PORT"]) { $cfg["DB_PORT"] } else { "5432" }

# --- pg_dump.exe ni topish (PATH, keyin eng yangi C:\Program Files\PostgreSQL\*\bin) ---
$pgDump = (Get-Command pg_dump.exe -ErrorAction SilentlyContinue).Source
if (-not $pgDump) {
    $pgDump = Get-ChildItem "C:\Program Files\PostgreSQL\*\bin\pg_dump.exe" -ErrorAction SilentlyContinue |
        Sort-Object { [int]($_.Directory.Parent.Name -replace '\D', '') } -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}
if (-not $pgDump) { throw "pg_dump.exe topilmadi. PostgreSQL o'rnatilganini tekshiring." }

# --- Zaxira ---
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$outFile = Join-Path $backupDir "prava_$stamp.dump"

$env:PGPASSWORD = $cfg["DB_PASSWORD"]
try {
    & $pgDump -h $dbHost -p $dbPort -U $dbUser -F c -f $outFile $dbName
    if ($LASTEXITCODE -ne 0) { throw "pg_dump xato bilan tugadi (kod $LASTEXITCODE)" }
} finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

$size = (Get-Item $outFile).Length
if ($size -le 0) { throw "Zaxira fayli bo'sh: $outFile" }
Write-Host ("Zaxira yaratildi: {0} ({1:N1} MB)" -f $outFile, ($size / 1MB))

# --- Eski nusxalarni tozalash: oxirgi $Keep tasi qoladi ---
$old = Get-ChildItem $backupDir -Filter "prava_*.dump" | Sort-Object Name -Descending | Select-Object -Skip $Keep
foreach ($f in $old) {
    Remove-Item $f.FullName
    Write-Host "Eski nusxa o'chirildi: $($f.Name)"
}
