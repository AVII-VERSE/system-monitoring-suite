# RATE_LIMITING Fix Plan

## Changes

- `dashboard.py`:
  - Implement `check_rate_limit`, `record_failed_attempt`, and `clear_failed_attempts` methods using `request.remote_addr`.
  - Enforce 5-attempt limit per 300s window on `/login` POST requests, returning HTTP 429 upon violation.

## Verification goals

- [x] Login endpoint rate limits after 5 failed attempts
- [x] Rate limited requests return HTTP 429
- [x] Successful login resets the counter
