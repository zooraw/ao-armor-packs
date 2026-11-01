param([string]$StateDirectory=(Join-Path $env:USERPROFILE '.ao-armor-packs'))
$ErrorActionPreference='Stop'
$python=Join-Path $StateDirectory '.venv\Scripts\python.exe'
& $python (Join-Path $PSScriptRoot 'src\install.py') uninstall --state $StateDirectory
if ($LASTEXITCODE -ne 0) { throw 'Uninstall refused; original database/settings have been preserved where possible. Inspect the reported error.' }
$shell=New-Object -ComObject WScript.Shell
foreach ($shortcut in @((Join-Path ([Environment]::GetFolderPath('Desktop')) 'AO Armor Packs.lnk'),(Join-Path ([Environment]::GetFolderPath('Desktop')) 'AO with AOU Armor.lnk'),(Join-Path ([Environment]::GetFolderPath('Startup')) 'AOU Live Armor.lnk'))) {
    if (Test-Path -LiteralPath $shortcut) {
        $link=$shell.CreateShortcut($shortcut)
        if ($link.Arguments.Contains((Join-Path $PSScriptRoot 'Start-ArmorPacks.ps1'))) { Remove-Item -LiteralPath $shortcut }
    }
}
Write-Output 'Armor controls removed. Private state/backups are retained outside the repository.'
