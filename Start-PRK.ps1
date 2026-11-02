param([string]$StateDirectory=(Join-Path $env:USERPROFILE '.prk-armor-packs'),[switch]$CompanionOnly,[switch]$Stop)
$ErrorActionPreference='Stop'
if(-not (Test-Path (Join-Path $StateDirectory 'installed.json'))){throw 'Install the separate PRK armor profile first'}
$configPath=Join-Path $StateDirectory 'config.json'
$config=Get-Content $configPath -Raw | ConvertFrom-Json
$controller=Join-Path $PSScriptRoot 'src\prk_controller.py'
if($Stop){& (Join-Path $StateDirectory '.venv\Scripts\python.exe') $controller --config $configPath --stop;return}
$target=[IO.Path]::GetFullPath((Join-Path $config.client 'AnarchyOnline.exe'))
$active=Get-Process -Name AnarchyOnline -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited -and $_.Path -eq $target}
$launcher=Join-Path (Split-Path $config.client) 'PRK.Launcher.exe'
$launcherState=Join-Path $StateDirectory 'launcher.json'
$reuseLauncher=$false
if(-not $CompanionOnly -and -not $active){
    $existing=Get-Process -Name PRK.Launcher -ErrorAction SilentlyContinue | Where-Object {-not $_.HasExited -and $_.Path -eq $launcher}
    if($existing){
        if((Test-Path -LiteralPath $launcherState) -and @($existing).Count -eq 1){
            $owned=Get-Content -LiteralPath $launcherState -Raw | ConvertFrom-Json
            $reuseLauncher=($owned.pid -eq $existing.Id -and $owned.path -eq $existing.Path -and $owned.created_ticks -eq $existing.StartTime.ToUniversalTime().Ticks)
        }
        if(-not $reuseLauncher){throw 'Close the existing PRK launcher once, then use PRK Armor Packs so it inherits material hot reload.'}
    }
}
Start-Process -FilePath (Join-Path $StateDirectory '.venv\Scripts\pythonw.exe') -ArgumentList ('"'+$controller+'" --config "'+$configPath+'"') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
if(-not $CompanionOnly -and -not $active -and -not $reuseLauncher){
    $prior=$env:RANDYVK_HOTRELOAD
    try{
        $env:RANDYVK_HOTRELOAD='1'
        $created=Start-Process -FilePath $launcher -WorkingDirectory (Split-Path $launcher) -WindowStyle Normal -PassThru
        @{pid=$created.Id;path=$created.Path;created_ticks=$created.StartTime.ToUniversalTime().Ticks} | ConvertTo-Json | Set-Content -LiteralPath $launcherState
    }
    finally{$env:RANDYVK_HOTRELOAD=$prior}
}
