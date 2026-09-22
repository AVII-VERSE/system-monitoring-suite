# ERROR_HANDLING Fix Plan

## Changes

- `dashboard.py`:
  - Register global error handlers for 400, 404, and 500 returning uniform JSON responses.
  - Enforce `debug=False` on production dashboard server.

## Verification goals

- [x] Global error handlers catch all unhandled exceptions
- [x] API responses contain generic JSON error messages with zero stack traces or system paths
- [x] Debug mode is turned off
