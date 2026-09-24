$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Workspace = Split-Path $Root -Parent
$IncludeModels = $args -contains '-IncludeModels'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$archive = Join-Path $Workspace "DeepPandaAI-backup-$stamp.zip"
$staging = Join-Path $env:TEMP "DeepPandaAI-export-$stamp"

New-Item -ItemType Directory -Force -Path $staging | Out-Null
$copyArgs = @($Root, $staging, '/E', '/COPY:DAT', '/DCOPY:DAT', '/R:1', '/W:1', '/XD', '.venv', '.pytest_cache', '.ruff_cache', '__pycache__', '.job-artifacts', '.media-work', '.memory-delete-backups', '/XF', '*.log', '/NP', '/NFL', '/NDL', '/NJH', '/NJS')
if (-not $IncludeModels) {
    $copyArgs += @('/XD', 'AI-Runtimes\OllamaModels', 'AI-Runtimes\ktransformers', 'AI-Runtimes\llama.cpp')
}
robocopy @copyArgs | Out-Null
if ($LASTEXITCODE -gt 7) { throw "Paket kaynaklari kopyalanamadi. Kod: $LASTEXITCODE" }

Compress-Archive -Path (Join-Path $staging '*') -DestinationPath $archive -CompressionLevel Optimal -Force
Remove-Item $staging -Recurse -Force

Write-Host "Export tamamlandi: $archive"
Write-Host "Modeller dahil: $IncludeModels"
Write-Host 'Geri yuklemek icin Restore-DeepPandaAI.cmd dosyasini kullanin.'
Read-Host 'Kapatmak icin Enter'
