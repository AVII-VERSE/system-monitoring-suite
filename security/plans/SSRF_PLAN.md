# SSRF Fix Plan

## Changes

- None required. Application has no user-supplied URL fetching features.

## Verification goals

- [x] No dynamic URL inputs accepted or fetched by backend code
- [x] Static system diagnostics fetch uses bounded timeout and hardcoded domain
