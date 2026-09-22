# SECRETS_EXPOSURE Fix Plan

## Changes

- `.gitignore` — Add rules for `logs/`, `*.key`, `encryption_key.txt`, `.env*`, and local sensitive files.
- `config.json` — Replace hardcoded plaintext credentials (`password123`, `darkwatch_super_secret_liquid_glass_key_2026`) with non-sensitive template defaults.
- `dashboard.py` — Update configuration loading to prioritize environment variables (`DARKWATCH_ADMIN_USER`, `DARKWATCH_ADMIN_PASSWORD`, `DARKWATCH_SESSION_SECRET`). Use `secrets.token_hex(32)` as dynamic session secret fallback instead of a fixed string. Remove hardcoded fallback `"password123"`.
- `logger_engine.py` — Allow reading Fernet encryption key from environment variable `DARKWATCH_ENCRYPTION_KEY` before falling back to local file. Untrack sensitive log files from git.
- `main.py` — Load `.env` automatically via `dotenv` if present, securely populating `os.environ`.

## New files

- `.env.example` — Documentation of environment variables with safe placeholder values.

## Verification goals

After implementation, ALL of these must be true:

- [ ] `git ls-files .env` returns nothing
- [ ] `git ls-files encryption_key.txt` returns nothing
- [ ] `git ls-files logs/` returns nothing (no active logs tracked in git)
- [ ] No hardcoded secret strings (`password123`, `darkwatch_super_secret...`) in `config.json` or source files
- [ ] `.env.example` exists with placeholder values only
- [ ] `grep -rn` for dangerous secret patterns across source files returns nothing
- [ ] No env var prefixed with NEXT_PUBLIC_, VITE_, or REACT_APP_ exists or contains secrets

## Manual verification (for the human)

- Test logging in with an environment variable password: `set DARKWATCH_ADMIN_PASSWORD=MySecurePass!2026` and verify authentication succeeds.
- Verify session cookies cannot be forged using old static secret keys.
