param(
    [Parameter(Mandatory=$true)][string]$ClientPath,
    [Parameter(Mandatory=$true)][string]$ProfilePath,
    [Parameter(Mandatory=$true)][string]$PreferencesPath,
    [string]$StateDirectory=(Join-Path $env:USERPROFILE '.prk-armor-packs'),
    [switch]$NoStart
)
$ErrorActionPreference='Stop'
$state=[IO.Path]::GetFullPath($StateDirectory)
if (($state.TrimEnd('\')+'\').StartsWith(([IO.Path]::GetFullPath($PSScriptRoot).TrimEnd('\')+'\'),[StringComparison]::OrdinalIgnoreCase)) { throw 'PRK state must stay outside this Git repository.' }
New-Item -ItemType Directory -Path $state -Force | Out-Null
$python=Join-Path $state '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & python -m venv (Join-Path $state '.venv')
    if($LASTEXITCODE -ne 0){throw 'PRK private Python environment creation failed'}
}
$requirements=Join-Path $PSScriptRoot 'requirements.txt'
$hash=(Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
$stamp=Join-Path $state 'requirements.sha256'
if (-not (Test-Path -LiteralPath $stamp) -or [IO.File]::ReadAllText($stamp).Trim() -ne $hash) {
    & $python -m pip install --disable-pip-version-check -r $requirements
    if($LASTEXITCODE -ne 0){throw 'PRK isolated dependency installation failed'}
    [IO.File]::WriteAllText($stamp,$hash)
}
& $python (Join-Path $PSScriptRoot 'src\prk_install.py') install --state $state --client $ClientPath --profile $ProfilePath --preferences $PreferencesPath
if($LASTEXITCODE -ne 0){throw 'PRK armor installation failed'}
$shell=New-Object -ComObject WScript.Shell
$link=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'PRK Armor Packs.lnk'))
$link.TargetPath=Join-Path $env:WINDIR 'System32\WindowsPowerShell\v1.0\powershell.exe'
$link.Arguments='-NoProfile -File "'+(Join-Path $PSScriptRoot 'Start-PRK.ps1')+'" -StateDirectory "'+$state+'"'
$link.WorkingDirectory=$PSScriptRoot;$link.WindowStyle=7;$link.Description='Project Rubi-Ka with live armor materials';$link.Save()
if(-not $NoStart){& (Join-Path $PSScriptRoot 'Start-PRK.ps1') -StateDirectory $state -CompanionOnly}
