# CORS Fix Plan

## Changes

- None required. Cross-origin access is disallowed by default; no wildcard origins configured.

## Verification goals

- [x] No `Access-Control-Allow-Origin: *` in responses
- [x] Browser Same-Origin Policy applies to all `/api/*` endpoints
