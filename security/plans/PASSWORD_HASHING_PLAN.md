# PASSWORD_HASHING Fix Plan

## Changes

- `dashboard.py`:
  - Integrate `werkzeug.security.generate_password_hash` (method `scrypt`) and `check_password_hash`.
  - Automatic migration of existing plaintext passwords to `scrypt` hashes upon launch.
  - Store `password_hash` in `config.json` instead of plaintext `password`.

## Verification goals

- [x] All administrator passwords stored using `scrypt` hashing
- [x] No MD5, SHA-1, or plain SHA-256 utilized
- [x] Legacy plaintext keys purged from configuration files
