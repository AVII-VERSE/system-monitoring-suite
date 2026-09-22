# CSRF Fix Plan

## Changes

- `dashboard.py`:
  - Enforce `SameSite=Lax` on all session cookies.
  - Require JSON payload parsing on state-changing API actions.

## Verification goals

- [x] Session cookies generated with `SameSite=Lax`
- [x] State-changing API endpoints reject plain form posts
