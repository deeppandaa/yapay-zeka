$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Binary = Get-ChildItem (Join-Path $Root 'AI-Runtimes\llama.cpp') -Filter 'llama-server.exe' -File -Recurse | Select-Object -First 1
$Model = Get-ChildItem (Join-Path $Root 'AI-Runtimes\models') -Filter '*.gguf' -File | Sort-Object Length -Descending | Select-Object -First 1
$Log = Join-Path $Root 'llama-cpp-server.log'
$ErrorLog = Join-Path $Root 'llama-cpp-server.err.log'
if (-not $Binary) { throw 'llama-server.exe bulunamadi.' }
if (-not $Model) { throw 'GGUF model bulunamadi.' }
$existing = Get-NetTCPConnection -LocalPort 8090 -State Listen -ErrorAction SilentlyContinue
if ($existing) { Write-Host 'llama.cpp zaten 8090 portunda calisiyor.'; exit 0 }
$arguments = @('-m', "`"$($Model.FullName)`"", '--host', '127.0.0.1', '--port', '8090', '-ngl', '0')
Start-Process -FilePath $Binary.FullName -ArgumentList $arguments -WorkingDirectory $Binary.Directory.FullName -RedirectStandardOutput $Log -RedirectStandardError $ErrorLog -WindowStyle Hidden
for ($i = 0; $i -lt 120; $i++) {
    try { Invoke-WebRequest 'http://127.0.0.1:8090/health' -UseBasicParsing -TimeoutSec 3 | Out-Null; Write-Host "llama.cpp hazir: $($Model.Name)"; exit 0 } catch { Start-Sleep -Milliseconds 500 }
}
throw 'llama.cpp server baslatilamadi.'
