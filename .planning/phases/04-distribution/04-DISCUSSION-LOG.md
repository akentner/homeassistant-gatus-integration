---
phase: 04
date: 2026-05-31
---

# Phase 04: Distribution — Discussion Log

## Areas Discussed

### README.md
- **Options presented:** Install + entities (recommended), Minimal, Full docs
- **Selected:** Install + entities
- **Notes:** Cover installation steps (HACS + manual), config flow fields, entity list per endpoint

### Validation Approach
- **Options presented:** Manual check, hassfest from HA core, Both
- **Selected:** Both + GitHub Actions (user specified HACS validate action from https://hacs.xyz/docs/publish/action/)
- **Notes:** CI with hacs/action@main + hassfest; manual check of existing files

### Brand Icon
- **User decision:** Use official Gatus logo from https://github.com/TwiN/gatus/blob/master/web/static/logo-512x512.png?raw=true, resize to 256×256 for brand/icon.png

## Deferred Ideas

None.
