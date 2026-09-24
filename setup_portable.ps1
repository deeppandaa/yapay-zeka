$ErrorActionPreference = 'Stop'
$Root = (Get-Location).Path
$Workspace = Split-Path $Root -Parent
$Venv = Join-Path $Root '.venv'
$Python = Join-Path $Venv 'Scripts\python.exe'
$ModelStore = Join-Path $Root 'AI-Runtimes\OllamaModels'

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Python Launcher (py) bulunamadi. Python 3.12+ kurun ve tekrar deneyin.'
}

if (-not (Test-Path $Python)) {
    & py -3 -m venv $Venv
}

& $Python -m pip install --upgrade pip
& $Python -m pip install -r (Join-Path $Root 'requirements.txt')
& $Python -m playwright install chromium

New-Item -ItemType Directory -Force -Path $ModelStore | Out-Null
[Environment]::SetEnvironmentVariable('OLLAMA_MODELS', $ModelStore, 'User')

$envFile = Join-Path $Root '.env'
@"
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=qwen3.6:latest
OLLAMA_EMBED_MODEL=nomic-embed-text
WORKSPACE_ROOT=$Workspace
MEMORY_DB=$Root\memory.db
MAX_UPLOAD_MB=265
AGENT_DEV_MODE=workspace
REQUIRE_MEMORY_APPROVAL=off
"@ | Set-Content -LiteralPath $envFile -Encoding utf8

Write-Output "Kurulum tamamlandi: $Root"
Write-Output "Model yolu: $ModelStore"
Write-Output 'Baslatmak icin: .\.venv\Scripts\python.exe -m uvicorn app:app --host 127.0.0.1 --port 8787'
Write-Output 'Ayrica Ollama servisini calistirin: ollama serve'
