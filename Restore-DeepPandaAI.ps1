$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Workspace = Split-Path $Root -Parent
$RestoreRoot = Join-Path $Workspace '.localqwen-restore-backups'
$Source = $args[0]
$Extracted = $null

if (-not $Source) {
    $Source = Read-Host 'Geri yuklenecek DeepPanda-Proje klasor yolunu yazin'
}
$Source = (Resolve-Path -LiteralPath $Source.Trim()).Path
if ([IO.Path]::GetExtension($Source).ToLowerInvariant() -eq '.zip') {
    $Extracted = Join-Path $env:TEMP "DeepPandaAI-restore-$([guid]::NewGuid().ToString('N'))"
    Expand-Archive -LiteralPath $Source -DestinationPath $Extracted -Force
    $Source = $Extracted
}
$SourceAI = Join-Path $Source 'Yapay Zeka'

if (-not (Test-Path $SourceAI)) {
    throw "Kaynakta 'Yapay Zeka' klasoru bulunamadi: $SourceAI"
}
if ((Resolve-Path $SourceAI).Path -eq (Resolve-Path $Root).Path) {
    throw 'Kaynak ve hedef ayni klasor olamaz.'
}

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$CurrentBackup = Join-Path $RestoreRoot $stamp
New-Item -ItemType Directory -Force -Path $CurrentBackup | Out-Null

Write-Host 'Mevcut Yapay Zeka durumu yedekleniyor...'
robocopy $Root $CurrentBackup /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XD '.venv' '.pytest_cache' '.ruff_cache' '__pycache__' /XF '*.log' /NP /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -gt 7) { throw "Mevcut durum yedeklenemedi. Kod: $LASTEXITCODE" }

Write-Host 'Geri yukleme yapiliyor...'
robocopy $SourceAI $Root /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XD '.venv' '.pytest_cache' '.ruff_cache' '__pycache__' /XF '*.log' /NP /NFL /NDL /NJH /NJS | Out-Null
if ($LASTEXITCODE -gt 7) { throw "Geri yukleme basarisiz. Kod: $LASTEXITCODE" }

$envFile = Join-Path $Root '.env'
@"
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.6:latest
WORKSPACE_ROOT=$Workspace
MEMORY_DB=$Root\memory.db
MAX_UPLOAD_MB=265
AGENT_DEV_MODE=workspace
"@ | Set-Content -LiteralPath $envFile -Encoding utf8

Write-Host ''
Write-Host 'Geri yukleme tamamlandi.'
Write-Host "Kaynak: $SourceAI"
Write-Host "Hedef:  $Root"
Write-Host "Mevcut durum yedegi: $CurrentBackup"
if (Test-Path (Join-Path $Root '.venv\Scripts\python.exe')) {
    $Python = Join-Path $Root '.venv\Scripts\python.exe'
    $compile = & $Python -m py_compile (Join-Path $Root 'app.py') 2>&1
    $compileCode = $LASTEXITCODE
    $tests = & $Python -m pytest (Join-Path $Root 'test_agent.py') -q 2>&1
    $testCode = $LASTEXITCODE
    $audit = [ordered]@{
        time = (Get-Date).ToString('o')
        compile_passed = ($compileCode -eq 0)
        test_output = ($tests -join "`n")
        test_passed = ($testCode -eq 0)
    }
    $audit | ConvertTo-Json | Set-Content (Join-Path $Root '.restore-self-audit.json') -Encoding utf8
    Write-Host "Self-audit raporu: $(Join-Path $Root '.restore-self-audit.json')"
}
if ($Extracted -and (Test-Path $Extracted)) { Remove-Item $Extracted -Recurse -Force }
Write-Host 'Baslatmak icin Start-LocalQwenAgent.cmd dosyasini calistirin.'
Read-Host 'Kapatmak icin Enter'
