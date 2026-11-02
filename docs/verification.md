# Verification scope

The preceding local prototype demonstrated custom armor rendering and initial
independent helmet/body/tank switches in a running regular-AO new-engine client.
It also passed native lookup/hash checks for eight custom and eight stock-HD
records. Those observations did not establish repeatable toggling: a user later
reported unchecking did not restore stock art.

The corrected runtime now marks the full cached staging source dirty before
every UpdateTexture call, including rollback/restoration. This follows the
[Direct3D9 dirty-region contract](https://learn.microsoft.com/en-us/windows/win32/direct3d9/texture-dirty-regions).
Each successful copy clears the source's dirty regions; returning success on a
later copy does not by itself establish that pixels were transferred.

This separate package has focused tests for optional integration, malformed
textures/preferences and database append preservation. Fresh-install database
selection is verified through the real client-native reader during installation.
Tests and native reads do not establish an observed in-game run. Fresh-login,
zoning and device-reset coverage must be reported separately.

Release validation results are updated below after running the package checks.

## Initial package validation

- Existing stock-HD prototype adopted through the public installer: all eight
  baseline resources passed the real client-native reader/hash/Close0 checks.
  Adoption left the game's database bytes unchanged.
- Repeated installation reported already installed, verified owned sources and
  repaired integration without appending resources again.
- Seven Python tests passed: optional controls absent/install/idempotence/remove,
  legacy migration, real-parser append/EOF roundtrip, malformed texture handling,
  named-preference parsing, partial rollback ownership and staging-file collision.
  These use generated fixtures, not a fresh AO install.
- A stateful Direct3D API model passed repeated cached off/on/off and shared-source
  transfers. This verifies the dirty-region contract, not real GPU pixels.
- The packaged companion attached to the already running game, reporting all
  eight stock targets without an error. A new visual checkbox test was not
  completed while the user was interacting with the game.
- Full uninstall, fresh-login, zoning and device reset remain unobserved. Do not
  describe fixture/adoption checks as that coverage.

## Fresh installation on a separate client

On 2026-11-01, a separate Windows machine cloned the public GitHub main commit
`f18dcbc2b69bd76f68cdb222e87a41710ad53198` and ran Install.ps1 with no legacy
adoption option and no existing armor-package marker. Regular AO was closed.

- Fresh-install state records `adopted_database: false`.
- All eight newly selected stock-HD records passed the real client-native
  lookup/hash checks; native close returned 0.
- The installed marker and all 16 custom/stock DDS inputs were present.
- The isolated environment used Python 3.14.3 and the pinned dependencies.
- The companion started successfully and reported waiting-for-game without
  an error.
- After this installation, the user reported that the requested armor testing
  passed: checking and unchecking the helmet/body and Tank Armor packs works,
  including returning to original artwork when disabled. This is user-confirmed
  visual validation; the agent did not perform or observe the in-game clicks.

This was an actual fresh armor-package installation, not legacy adoption or a
synthetic database test. No uninstall, repeated test suite or extra restart
cycle was performed for this focused check.

Real paths, private logs and screenshots are intentionally excluded from Git.

## Project Rubi-Ka profile

The separate PRK implementation and its executed checks are documented in
[PRK validation](PRK.md#executed-validation). Its actual GUI checkbox pairs
added/removed the correct material files with the companion live and renderer
hot reload enabled. Equipped rendering remains unobserved; the new account's
appearance test was explicitly waived. Retail validation above does not establish
PRK rendering behavior.
