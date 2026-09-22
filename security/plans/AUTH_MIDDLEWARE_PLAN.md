# AUTH_MIDDLEWARE Fix Plan

## Changes

- `dashboard.py`:
  - Add session cookie security parameters (`SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, `PERMANENT_SESSION_LIFETIME = timedelta(hours=12)`).
  - Implement a global `before_request` security filter enforcing authentication across all endpoints by default (fail-closed architecture).
  - Maintain an explicit public route allowlist: `['/login', '/favicon.ico']` and anything under `/static/`.
  - Call `session.clear()` upon successful login to prevent session fixation attacks.
  - Ensure unauthenticated API requests return 401 JSON, and unauthenticated HTML navigation requests redirect to `/login`.

## New files

- None required (all middleware integrated into core web framework).

## Verification goals

After implementation, ALL of these must be true:

- [ ] Every API endpoint (`/api/*`) returns HTTP 401 when accessed without an active session
- [ ] Root dashboard (`/`) redirects with HTTP 302 to `/login` when accessed without an active session
- [ ] Auth middleware runs globally before any route handler executes
- [ ] Session cookie includes `HttpOnly` and `SameSite=Lax` attributes
- [ ] Authenticated login grants access and creates an isolated session

## Manual verification (for the human)

- Open an Incognito/Private browser window and navigate directly to `http://127.0.0.1:5000/api/stats` and verify an unauthorized 401 JSON response is displayed.
- Attempt to navigate to `http://127.0.0.1:5000/` and verify seamless redirection to `http://127.0.0.1:5000/login`.
