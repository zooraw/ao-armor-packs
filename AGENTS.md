# AO Armor Packs contributor instructions

- Preserve the user's requested scope. Use explicit game/GUI/preferences paths.
  Never infer an AO install from a private hardcoded developer path.
- The base AOU package has no armor controls. Integration belongs to this installer:
  validate the installed pack before inserting owned XML blocks; uninstall removes
  them. Do not add permanently visible armor entries back into the base GUI.
- Keep real config/state, account data, game extracts, DDS/FCTX records, database
  backups and logs outside Git. Examples must be generic. Check exact staged files,
  binary metadata, commit messages and intentionally public author identity before
  publishing. Never publish OS usernames, home paths, private hosts or identifiers.
- Public PNGs are the selected custom artwork with metadata removed. Original
  stock texture records must be extracted from each user's client locally.
- Do not write a live AO database. Hash-check the supported DLL build, source art,
  stock identities and ownership first. Preserve unrelated index bytes, native EOF
  markers, allocation headers and UV aspect ratios. Native reader checks are
  required for newly selected database payloads. PRK is a separate target.
- Maintain explicit ownership even when data is malformed. Roll back only bytes
  still matching this operation; never overwrite another writer's changes.
- D3D9 UpdateTexture consumes staging dirty regions. Call AddDirtyRect(NULL)
  before EVERY cached source upload, including rollback/restoration. HRESULT
  success does not prove rendered pixels changed. Preserve the repeat-toggle fix.
- Reuse the existing renderer discovery and fixed hashes. Do not repeat broad
  investigation. Update verification.md when materially different behavior is
  observed. Distinguish synthetic tests, native reads and actual in-game checks.
- Use proportionate checks: focused integration/format regressions, Python/JS/
  PowerShell syntax, and an actual off/on/off run when the user is logged in.
  Do not request or operate authentication or password managers.
- Preserve GPL notices and upstream credits. Keep new code modular and clear.
