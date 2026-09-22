# ACCESS_CONTROL Fix Plan

## Changes

- `dashboard.py`:
  - Enforce `secure_filename(os.path.basename(filename))` and regex check `^[a-zA-Z0-9_.-]+$` on all dynamic file retrieval endpoints.
  - Verify canonical absolute path prefix matches designated storage directory.

## New files

- None.

## Verification goals

- [x] Path traversal attempts (`..`, `/`, `\`) fail validation and return 400/404
- [x] Legitimate files within category directories serve correctly
- [x] Requests to non-existent categories return 400
