# SECRETS_EXPOSURE Security Report

## Status: PASS (Remediated)
*Initial Assessment Status: CRITICAL*

## Findings

During the comprehensive scan of the repository, multiple critical secret exposure vulnerabilities were identified and subsequently remediated:

1. **Hardcoded Credentials & Session Secrets in Git-Tracked Config (`config.json`)**:
   `config.json` was tracked in git and contained plaintext administrative credentials and static Flask session secret:
   ```json
   "dashboard": {
     "enabled": true,
     "host": "127.0.0.1",
     "port": 5000,
     "auth_required": true,
     "username": "admin",
     "password": "password123",
     "session_secret": "darkwatch_super_secret_liquid_glass_key_2026"
   }
   ```
   **Remediation**: Plaintext credentials, static secrets, and default passwords have been completely purged from `config.json`. A sanitized template `config.example.json` was created.

2. **Hardcoded Fallback Credentials in Source Code (`dashboard.py`)**:
   In `dashboard.py`, default credentials were hardcoded as fallbacks (`valid_pass = dashboard_cfg.get("password", "password123")`).
   **Remediation**: Hardcoded `"password123"` has been removed. `dashboard.py` now retrieves credentials dynamically using environment variables (`DARKWATCH_ADMIN_USER` and `DARKWATCH_ADMIN_PASSWORD`), prevents timing attacks using `hmac.compare_digest`, and generates cryptographically secure ephemeral passwords via `secrets.token_urlsafe` if unconfigured.

3. **Static Session Secret Key**:
   Flask session cookie signing used a static, leaked string key.
   **Remediation**: `dashboard.py` now prioritizes `DARKWATCH_SESSION_SECRET` from the environment, falling back to a newly generated 256-bit cryptographically secure token (`secrets.token_hex(32)`).

4. **Sensitive Surveillance & Keystroke Logs Tracked in Git Repository**:
   The `logs/` directory contained active keystroke logs (`logs/key_log.txt`), clipboard captures (`logs/clipboard.txt`), system diagnostic info (`logs/systeminfo.txt`), and screenshot images tracked by git.
   **Remediation**: All files under `logs/` were purged from git tracking via `git rm --cached -r logs/`. Specific ignore rules for `logs/`, `*.key`, `encryption_key*.txt`, and surveillance captures were added to `.gitignore`.

5. **Missing `.env.example`**:
   **Remediation**: Created `.env.example` with non-sensitive placeholders documenting all configuration parameters (`DARKWATCH_ADMIN_USER`, `DARKWATCH_ADMIN_PASSWORD`, `DARKWATCH_SESSION_SECRET`, `DARKWATCH_ENCRYPTION_KEY`, etc.). Added `.env` loader in `main.py`.

## What's at risk

- **Dashboard Takeover / Privilege Escalation**: Anyone with read access to the repository (or git clone) could log into the DarkWatch dashboard using the known credentials `admin` / `password123`.
- **Session Forgery**: Because `session_secret` was fixed and published (`darkwatch_super_secret_liquid_glass_key_2026`), an attacker could craft forged Flask session cookies to authenticate as `admin` without needing the password.
- **Data Exfiltration of Harvested Keystrokes / Telemetry**: Tracked log files in the repository leaked sensitive keystrokes, clipboard data, and machine diagnostics to anyone inspecting the git tree.
- **Cryptographic Failure**: Leaked encryption keys (`encryption_key.txt`) allow instant decryption of encrypted surveillance records.

## What's already secure

- `.gitignore` correctly ignores `.env`, `.venv`, `env/`, and Python cache directories (`__pycache__/`).
- Frontend files (`static/js/dashboard.js`, `templates/`) do not contain third-party API secret tokens or hardcoded client-side API keys.
- Secrets are not bundled into public frontend build variables.

## Verification Results

| Goal | Expected | Actual Result | Status |
|------|----------|---------------|--------|
| `git ls-files .env` | Empty | Returned nothing | **PASS** |
| `git ls-files encryption_key.txt` | Empty | Returned nothing | **PASS** |
| `git ls-files logs/` | Empty | Returned nothing (15 files untracked) | **PASS** |
| Secret strings in `config.json` | None | Cleaned, `password123` removed | **PASS** |
| `.env.example` existence | Present | Created with placeholder values | **PASS** |
| Hardcoded fallback credentials | Removed | Dynamic env vars + `secrets.token_urlsafe` | **PASS** |
| Grep search for dangerous tokens | None | No active secrets detected | **PASS** |
