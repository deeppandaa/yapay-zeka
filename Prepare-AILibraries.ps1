$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Target = Join-Path $Root 'AI-Libraries'
$Catalog = Join-Path $Root 'library_catalog.json'
New-Item -ItemType Directory -Force -Path $Target | Out-Null
$items = Get-Content $Catalog -Raw | ConvertFrom-Json
foreach ($item in $items) {
    $destination = Join-Path $Target $item.name
    if (Test-Path (Join-Path $destination '.git')) {
        git -C $destination pull --ff-only
    } else {
        git clone --depth 1 $item.repo $destination
    }
}
& (Join-Path $Root '.venv\Scripts\python.exe') (Join-Path $Root 'learn_git_libraries.py')
Write-Host "Kutuphaneler hazir ve yerel hafizaya indekslendi: $Target"
