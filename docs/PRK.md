# Project Rubi-Ka armor profile

This separate profile supports the inspected **00.7.2_EP1 PRK client with
ao-vk 0.8.1**. It does not use the retail D3D9 backend, touch the retail AO
installation, rewrite PRK's SQLite database or replace its renderer/browser DLLs.
Exact executable/renderer/Utils hashes are checked before installation.

Install the separate **PRK_aou_mod** GUI first. It provides the namespaced
`PRK_AOU_CYT`, `PRK_AOU_Slim_CNI` and `PRK_AOU_Slim_CNT` layouts. The regular
AOU layouts and the retail `Install.ps1` armor path are not the PRK installer.

## Install and launch

Close the PRK game and launcher normally. With Python 3.13 or 3.14 available,
run this repository's PRK installer, replacing the generic paths:

```powershell
.\Install-PRK.ps1 -ClientPath 'C:\Games\Project Rubi-Ka\client' -ProfilePath 'C:\LocalPrefs\PRK\client' -PreferencesPath 'C:\LocalPrefs\PRK\client\Prefs\Account\Prefs.xml'
```

The client is the folder containing `AnarchyOnline.exe`, `randy31.dll`,
`randy-vk` and `cd_image/rdb.db`. The profile is the PRK AppData folder containing
`Gui`, `Prefs` and `scripts`; choose the account's Prefs.xml, not a character file.
Private state defaults to `%USERPROFILE%\.prk-armor-packs`, separate from retail.

Use the **PRK Armor Packs** desktop shortcut. It starts the companion and the PRK
launcher with `RANDYVK_HOTRELOAD=1` only in that launch environment. It does not
change global environment settings. If an older PRK launcher is still open,
close it once and use the shortcut so its client inherits the flag.
Handle launcher/login normally yourself.
The shortcut reuses a launcher it started, verified by its process creation time;
it does not replace an unrelated existing launcher.

With the companion running and material hot reload enabled, **AOU > Armor Packs**
or **F10 > Armor Packs** controls helmet/body and tank independently. Checked
adds the owned custom albedo maps; unchecked removes them and lets the renderer
use stock artwork. No restart is required for those choices. The renderer's
albedo-map setting must be on (the installed test configuration already had it on).
The base PRK AOU GUI has no armor controls before this optional profile is installed.

Starting an already running PRK client without the hot-reload flag cannot enable
it retroactively. The companion reports `restart-required`; use the shortcut on
the next normal start. Status is in the private state's controller-status.json.

## Why this route is PRK-specific

The installed ao-vk renderer side-loads `1010004_<id>_d.png` from
`randy-vk/materials` and watches additions/removals when hot reload is enabled.
The installer verifies all eight original SQLite resource rows, selected custom
artwork hashes, UV aspect ratios and opaque RGB565 pixels. It refuses conflicting
maps rather than overwriting other packs.

PRK can CPU-compose keyed garments. These eight Omni-AF records have no RGB565
green-key pixels, so the inspected CAT code's opaque path retains their original
resource-tagged texture and makes renderer overrides applicable. This reasoning
is based on the actual client code/resources and upstream renderer source; it is
not an observed equipped-armor rendering test. Green-keyed garments require a
different path and are deliberately rejected. Do not generalize this profile
to arbitrary clothing or another renderer build.

The source contract is described in ao-vk's
[material documentation](https://github.com/wannabuh/ao-vk/blob/a3ff63185a2ae3ce81bbe600fda23e1523acd9cc/docs/materials.md)
and [material loader](https://github.com/wannabuh/ao-vk/blob/a3ff63185a2ae3ce81bbe600fda23e1523acd9cc/proxy/ddraw/rvk_materials.cpp).

## Remove and maintain

Close PRK, then run `Uninstall-PRK.ps1` using the same `-StateDirectory` if it
was customized. It stops this companion, removes only owned albedo files, restores
the exact pre-armor GUI bytes and removes its shortcut. It does not alter the
SQLite database. Remove armor before reinstalling/removing the PRK GUI, because
the optional controls modify files owned by that GUI installer.

Keep the source folders in place while installed. Client/renderer updates fail
the hash guard until reviewed. Keep config, resource extracts, logs and private
evidence outside Git. The user's new account cannot equip this armor, so the
equipped appearance check was explicitly waived; it must not be reported as tested.

## Executed validation

- All eight actual PRK stock JPEG resources, custom artwork hashes, aspect ratios
  and opaque CAT fast-path requirements passed the installer checks.
- The optional integration retains all 153 native PRK settings bindings in each
  of the three PRK AOU layouts and adds the two armor choices.
- A bounded observer attached to the running PRK client and loaded its native
  preference ABI successfully, then detached. It correctly reported that the old
  launch lacked the hot-reload flag.
- After normal shutdown and deployment, one independent on/off pair per group
  produced 7/0 body sidecars and 1/0 tank sidecars. The saved choices were restored.
  These are filesystem/backend checks, not rendered-pixel or checkbox-click tests.
- The new shortcut restarted the launcher with its hot-reload flag verified in
  that process. After login, the renderer logged eight material maps with hot
  reload enabled, and the companion reported `live` without errors.
- In the running PRK GUI, one off/on pair per checkbox reached the companion:
  disabling helmet/body removed its seven maps while retaining the tank map;
  disabling tank removed its one map while retaining the seven body maps.
  Re-enabling each restored its maps. Both choices were left enabled. This
  verifies the actual UI-to-backend path, not equipped rendered pixels.
- Ten focused tests passed, including opaque/keyed detection, independent groups,
  external-file ownership and safe removal with missing source art.
- No equipped-armor appearance was observed; the user waived that test because
  this is a new account. No authentication or password-manager UI was operated.
