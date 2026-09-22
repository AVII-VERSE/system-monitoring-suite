# SECURITY_HEADERS Fix Plan

## Changes

- `dashboard.py`:
  - Implement `@self.app.after_request` handler setting `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`, and conditional `Strict-Transport-Security`.

## Verification goals

- [x] All 5 required security headers present on every response
- [x] Headers applied via a single global hook
