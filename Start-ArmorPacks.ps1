param(
    [string]$StateDirectory=(Join-Path $env:USERPROFILE '.ao-armor-packs'),
    [switch]$CompanionOnly,
    [switch]$Stop
)
$ErrorActionPreference='Stop'
$configPath=Join-Path $StateDirectory 'config.json'
if (-not (Test-Path -LiteralPath (Join-Path $StateDirectory 'installed.json'))) { throw 'AO Armor Packs is not installed. Run Install.ps1 first.' }
$controller=Join-Path $PSScriptRoot 'src\controller.py'
if ($Stop) {
    & (Join-Path $StateDirectory '.venv\Scripts\python.exe') $controller --config $configPath --stop
    if ($LASTEXITCODE -ne 0) { throw 'Could not request companion stop.' }
    return
}
$config=Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$pythonw=Join-Path $StateDirectory '.venv\Scripts\pythonw.exe'
Start-Process -FilePath $pythonw -ArgumentList ('"'+$controller+'" --config "'+$configPath+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
if (-not $CompanionOnly) {
    $target=[IO.Path]::GetFullPath((Join-Path $config.game 'AnarchyOnline.exe'))
    $active=Get-Process -Name AnarchyOnline -ErrorAction SilentlyContinue | Where-Object { -not $_.HasExited -and $_.Path -eq $target }
    if (-not $active) { Start-Process -FilePath (Join-Path $config.game 'Anarchy.exe') -WorkingDirectory $config.game -WindowStyle Normal }
}
