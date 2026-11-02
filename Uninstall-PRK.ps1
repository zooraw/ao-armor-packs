param([string]$StateDirectory=(Join-Path $env:USERPROFILE '.prk-armor-packs'))
$ErrorActionPreference='Stop'
& (Join-Path $StateDirectory '.venv\Scripts\python.exe') (Join-Path $PSScriptRoot 'src\prk_install.py') uninstall --state $StateDirectory
if($LASTEXITCODE -ne 0){throw 'PRK armor uninstall refused; inspect the ownership error'}
$shortcut=Join-Path ([Environment]::GetFolderPath('Desktop')) 'PRK Armor Packs.lnk'
if(Test-Path $shortcut){
    $link=(New-Object -ComObject WScript.Shell).CreateShortcut($shortcut)
    if($link.Arguments.Contains((Join-Path $PSScriptRoot 'Start-PRK.ps1'))){Remove-Item -LiteralPath $shortcut}
}
