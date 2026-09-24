$ErrorActionPreference = 'Stop'

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = Join-Path $Root '.venv\Scripts\python.exe'
$ModelStore = Join-Path $Root 'AI-Runtimes\OllamaModels'
$BrowserData = Join-Path $env:TEMP 'LocalQwenAgent-AppWindow'
$OllamaProcess = $null
$AgentProcess = $null
$OllamaStarted = $false
$AgentStarted = $false
$LauncherMutex = New-Object System.Threading.Mutex($false, 'LocalQwenAgent.SingleLauncher')
if (-not $LauncherMutex.WaitOne(0)) {
    Write-Host 'LocalQwenAgent zaten acik.'
    exit 0
}

function Test-LocalPort {
    param([int]$Port)
    return [bool](Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort $Port -State Listen -ErrorAction SilentlyContinue)
}

function Wait-Endpoint {
    param([string]$Uri, [int]$Seconds = 30)
    for ($i = 0; $i -lt ($Seconds * 2); $i++) {
        try {
            Invoke-WebRequest -Uri $Uri -UseBasicParsing -TimeoutSec 3 | Out-Null
            return
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Servis baslatilamadi: $Uri"
}

function Get-AppBrowserProcess {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -in @('msedge.exe', 'chrome.exe') -and
            $_.CommandLine -and
            $_.CommandLine.Contains("--user-data-dir=$BrowserData")
        }
}

try {
    if (-not (Test-Path $Python)) {
        throw "Python sanal ortami bulunamadi: $Python"
    }

    if (-not (Test-LocalPort 11434)) {
        $env:OLLAMA_MODELS = $ModelStore
        $OllamaProcess = Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WorkingDirectory $Root -PassThru -WindowStyle Hidden
        $OllamaStarted = $true
        Wait-Endpoint 'http://127.0.0.1:11434/api/tags' 45
    }

    if (-not (Test-LocalPort 8787)) {
        $AgentProcess = Start-Process -FilePath $Python -ArgumentList '-m', 'uvicorn', 'app:app', '--host', '127.0.0.1', '--port', '8787' -WorkingDirectory $Root -PassThru -WindowStyle Hidden
        $AgentStarted = $true
        Wait-Endpoint 'http://127.0.0.1:8787/api/status' 30
    }

    $browserCandidates = @(
        (Get-Command msedge.exe -ErrorAction SilentlyContinue).Source,
        (Get-Command chrome.exe -ErrorAction SilentlyContinue).Source,
        (Join-Path ${env:ProgramFiles} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\Edge\Application\msedge.exe'),
        (Get-ChildItem (Join-Path ${env:ProgramFiles(x86)} 'Microsoft\EdgeCore') -Filter 'msedge.exe' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName),
        (Join-Path ${env:LOCALAPPDATA} 'Microsoft\Edge\Application\msedge.exe'),
        (Join-Path ${env:ProgramFiles} 'Google\Chrome\Application\chrome.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Google\Chrome\Application\chrome.exe'),
        (Join-Path ${env:LOCALAPPDATA} 'Google\Chrome\Application\chrome.exe'),
        (Get-ChildItem (Join-Path ${env:LOCALAPPDATA} 'ms-playwright') -Filter 'chrome.exe' -File -Recurse -ErrorAction SilentlyContinue | Select-Object -First 1 -ExpandProperty FullName)
    ) | Where-Object { $_ -and (Test-Path $_) }
    if (-not $browserCandidates) {
        throw 'Microsoft Edge veya Google Chrome bulunamadi.'
    }
    $browserPath = $browserCandidates[0]

    New-Item -ItemType Directory -Force -Path $BrowserData | Out-Null
    Start-Process -FilePath $browserPath -ArgumentList @('--app=http://127.0.0.1:8787/', "--user-data-dir=$BrowserData") | Out-Null
    Write-Host 'LocalQwenAgent acildi. Pencereyi kapatinca baslatilan servisler durdurulacak.'

    for ($i = 0; $i -lt 30 -and -not (Get-AppBrowserProcess); $i++) {
        Start-Sleep -Milliseconds 500
    }
    while (Get-AppBrowserProcess) {
        Start-Sleep -Seconds 1
    }
}
finally {
    if ($AgentStarted -and $AgentProcess -and -not $AgentProcess.HasExited) {
        taskkill.exe /PID $AgentProcess.Id /T /F | Out-Null
    }
    if ($OllamaStarted -and $OllamaProcess -and -not $OllamaProcess.HasExited) {
        taskkill.exe /PID $OllamaProcess.Id /T /F | Out-Null
    }
    $LauncherMutex.ReleaseMutex()
    $LauncherMutex.Dispose()
}
