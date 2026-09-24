$ErrorActionPreference = 'Stop'

$ContinueRoot = Join-Path $env:USERPROFILE '.continue'
$Config = Join-Path $ContinueRoot 'config.yaml'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = "$Config.$stamp.bak"

New-Item -ItemType Directory -Force -Path $ContinueRoot | Out-Null
if (Test-Path $Config) {
    Copy-Item $Config $backup -Force
    Write-Host "Mevcut Continue config yedeklendi: $backup"
}

@"
name: LocalQwenAgent
version: 1.0.0
schema: v1
models:
  - name: local-qwen
    provider: openai
    model: local-qwen
    apiBase: http://127.0.0.1:8787/v1
    apiKey: local-only
"@ | Set-Content -LiteralPath $Config -Encoding utf8

Write-Host "Continue config hazir: $Config"
Write-Host 'VS Code icinde Developer: Reload Window calistirin.'
Read-Host 'Kapatmak icin Enter'
