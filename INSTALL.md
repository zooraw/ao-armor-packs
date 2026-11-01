# Install AO Armor Packs v1.0.0

## Before you start

You need Windows, the regular AO **18.8.62_EP2 new-engine client**, an installed
[AOU GUI](https://github.com/zooraw/aou_mod), and Python **3.13 or 3.14** available
as `python`. The installer checks exact supported client DLL hashes. Project
Rubi-Ka is a separate client and is not supported by this release.

Internet access is needed for the first dependency installation. No password or
game account credentials are required by the armor installer.

## Download and extract

1. Download **AO-Armor-Packs-v1.0.0.zip** from the release's **Assets** section.
2. Right-click the ZIP and choose **Extract All**. Keep the extracted folder in
   a permanent location, such as `C:\Games\AO-Armor-Packs-v1.0.0`.
3. Close regular AO normally. Open PowerShell in the extracted folder containing
   `Install.ps1`. Do not run the installer from inside the ZIP.

The ZIP contains the artwork, companion, installer and these instructions. You
do not need Git or a separate compiled installer.

## Find your three local paths

| Parameter | What to select |
| --- | --- |
| `GamePath` | The regular AO folder containing `Anarchy.exe` and `AnarchyOnline.exe`. |
| `GuiPath` | The AO AppData `Gui` folder containing `AOU_CYT`, `AOU_Slim_CNI` or `AOU_Slim_CNT`. |
| `PreferencesPath` | The exact account's `Prefs.xml`, not a character's preferences file. |

For the last two, enter `%LOCALAPPDATA%\Funcom\Anarchy Online` in File Explorer.
Open the correct installation folder, then `Anarchy Online`. Its `Gui` directory
is `GuiPath`; under its `Prefs` directory, select your account's `Prefs.xml`.
If several installs/accounts are present, choose the one you actually play.

## Run the installer

Replace these **example paths** with your own:

```powershell
.\Install.ps1 -GamePath 'C:\Games\Anarchy Online' -GuiPath 'C:\LocalPrefs\Gui' -PreferencesPath 'C:\LocalPrefs\Prefs\Account\Prefs.xml'
```

If Windows blocks the downloaded script, you can launch this reviewed installer
with a process-only execution-policy override; it does not change the system
policy:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\Install.ps1 -GamePath 'C:\Games\Anarchy Online' -GuiPath 'C:\LocalPrefs\Gui' -PreferencesPath 'C:\LocalPrefs\Prefs\Account\Prefs.xml'
```

The installer creates a private environment/state under
`%USERPROFILE%\.ao-armor-packs`, checks the artwork/client, prepares stock-HD
textures, verifies all eight records with AO's native reader, and adds the optional
armor controls and a desktop shortcut. Original stock textures and private
settings are obtained locally and are not included in the download.

Optional: add `-StartWithWindows` to start only the companion at Windows sign-in.
Leave the extracted folder in place: the shortcut runs the companion from it.
If installation reports an unsupported build or verification failure, stop and
read that error; do not bypass the checks.

## Play and switch armor

Use the **AO Armor Packs** desktop shortcut, log in normally, and equip the armor.
Open **AOU > Armor Packs** or **F10 > Armor Packs**:

- **Checked / [x]:** custom artwork.
- **Unchecked / [ ]:** original artwork.
- Helmet/body and Tank Armor switch independently while the companion runs.

The base AOU GUI has no armor controls until this package is installed.

## Remove or get installation help

Close AO normally, then run `Uninstall.ps1` from the same extracted folder.
It restores the owned pre-install database checkpoint and removes its controls
and shortcuts. Private backups remain local. See [README.md](README.md) for
ownership checks and [verification](docs/verification.md) for tested coverage.

For help finding paths and running the installer, give your AI assistant
[INSTALL_WITH_AI.md](INSTALL_WITH_AI.md). It contains a ready-to-copy prompt and
the complete installation procedure.
