<# Install the separate armor pack. All configuration/state stays outside Git. #>
param(
    [Parameter(Mandatory=$true)][string]$GamePath,
    [Parameter(Mandatory=$true)][string]$GuiPath,
    [Parameter(Mandatory=$true)][string]$PreferencesPath,
    [string]$StateDirectory = (Join-Path $env:USERPROFILE '.ao-armor-packs'),
    [string]$AdoptLegacyState,
    [switch]$StartWithWindows,
    [switch]$NoStart
)
$ErrorActionPreference='Stop'
$repo=$PSScriptRoot
$state=[IO.Path]::GetFullPath($StateDirectory)
$repoFull=[IO.Path]::GetFullPath($repo).TrimEnd('\')+'\'
if (($state.TrimEnd('\')+'\').StartsWith($repoFull,[StringComparison]::OrdinalIgnoreCase)) { throw 'StateDirectory must stay outside the Git repository.' }
New-Item -ItemType Directory -Path $state -Force | Out-Null
$python=Join-Path $state '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    & python -m venv (Join-Path $state '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'Python venv creation failed. Install Python 3.13 first.' }
}
$requirements=Join-Path $repo 'requirements.txt'
$requirementHash=(Get-FileHash -LiteralPath $requirements -Algorithm SHA256).Hash
$stamp=Join-Path $state 'requirements.sha256'
if (-not (Test-Path -LiteralPath $stamp) -or ([IO.File]::ReadAllText($stamp)).Trim() -ne $requirementHash) {
    & $python -m pip install --disable-pip-version-check -r $requirements
    if ($LASTEXITCODE -ne 0) { throw 'Private environment dependency installation failed.' }
    [IO.File]::WriteAllText($stamp,$requirementHash)
}
$arguments=@((Join-Path $repo 'src\install.py'),'install','--state',$state,'--game',$GamePath,'--gui',$GuiPath,'--preferences',$PreferencesPath)
if ($AdoptLegacyState) { $arguments+=@('--adopt-legacy-state',$AdoptLegacyState) }
& $python @arguments
if ($LASTEXITCODE -ne 0) { throw 'Armor installation failed; inspect the local error before retrying.' }
$shell=New-Object -ComObject WScript.Shell
$launcher=Join-Path $repo 'Start-ArmorPacks.ps1'
$powershell=Join-Path $PSHOME 'powershell.exe'
if (-not (Test-Path -LiteralPath $powershell)) { $powershell=(Get-Command pwsh.exe -ErrorAction Stop).Source }
$link=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Desktop')) 'AO Armor Packs.lnk'))
$link.TargetPath=$powershell
$link.Arguments='-NoProfile -File "'+$launcher+'" -StateDirectory "'+$state+'"'
$link.WorkingDirectory=$repo;$link.WindowStyle=7;$link.Description='Start local AO armor companion and normal game launcher';$link.Save()
if ($StartWithWindows) {
    $startup=$shell.CreateShortcut((Join-Path ([Environment]::GetFolderPath('Startup')) 'AOU Live Armor.lnk'))
    $startup.TargetPath=$powershell
    $startup.Arguments=$link.Arguments+' -CompanionOnly'
    $startup.WorkingDirectory=$repo;$startup.WindowStyle=7;$startup.Description='Local AO Armor Packs companion';$startup.Save()
}
if (-not $NoStart) { & $launcher -StateDirectory $state -CompanionOnly }
Write-Output 'AO Armor Packs installed. Use the desktop shortcut, then AOU > Armor Packs or F10 > Armor Packs.'
