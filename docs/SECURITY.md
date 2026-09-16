# Security & DevSecOps Architecture

## 1. Secrets Protection
- **Zero Client Exposure**: Database service-role keys, OAuth refresh tokens, and AI API keys are stored solely on the local backend and never bundled into the client distribution.
- **AES-256 Fernet Encryption**: Sensitive database columns (`access_token_encrypted`, `refresh_token_encrypted`) are encrypted at rest using keys derived from `APP_SECRET_KEY`.

## 2. File & Command Injection Prevention
- **Path Sanitization**: All incoming video filenames are sanitized via `security.sanitize_filename` to strip path traversal sequences (`..`, `/`, `\`).
- **Path Confinement**: Target paths are strictly validated against `YT_AUTOMATION_ROOT` using `security.validate_safe_path`.
- **Safe FFmpeg Execution**: Media inspection commands are invoked as explicit parameter lists without shell interpolation (`shell=False`).

## 3. Database Security & RLS
- Supabase PostgreSQL Row Level Security (RLS) is enabled across all 21 tables.
- Access policies guarantee that users can only inspect and modify channels and videos associated with their workspace ID.
