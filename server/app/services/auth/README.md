# Authentication Service (`app.services.auth`)

Provides user registration, Argon2id password hashing, credential authentication, signed JWT session & refresh token lifecycle, token rotation, and CSRF protection.

## Responsibilities
- **Registration**: Registers new accounts, rejects duplicate emails with typed 409 Conflict errors, and securely hashes passwords with Argon2id before database storage.
- **Authentication**: Validates credentials using constant-time verification, mitigates user-enumeration timing attacks, and generates signed HS256 JWT access and refresh tokens.
- **Token Lifecycle & Rotation**: Issues short-lived access tokens (15m) and long-lived refresh tokens (7d). Rotates refresh tokens on every refresh call, detecting and revoking replayed tokens.
- **CSRF Defense**: Issues cryptographically secure Double-Submit CSRF tokens and enforces verification headers on state-changing API operations.
- **Sanitization**: Strictly purges passwords and password hashes from API responses (`UserRead`).

## Security Invariants
- **Never Plaintext**: Plaintext passwords are never written to disk, database, or structlog logs.
- **Argon2id Parameters**: OWASP-compliant memory cost (64 MB), time cost (3), parallelism (4), and salt length (16 bytes).
- **Cookie Security**:
  - `auth_token`: `HttpOnly=True`, `SameSite=Lax`, `path="/"`, `Secure=True` (in staging/production).
  - `refresh_token`: `HttpOnly=True`, `SameSite=Lax`, `path="/api/v1/auth"`, `Secure=True` (in staging/production).
  - `csrf_token`: `HttpOnly=False` (accessible to client SPA), `SameSite=Lax`, `path="/"`.
- **Replay Protection**: Old refresh tokens are invalidated upon rotation; reuse of an invalidated refresh token triggers immediate rejection with 401 Unauthorized.

## Public Interface
- `AuthService.register_user(payload: UserRegisterRequest) -> UserRead`
- `AuthService.authenticate_user(payload: UserLoginRequest) -> tuple[UserRead, str, str]`
- `AuthService.refresh_session(raw_refresh_token: str) -> tuple[UserRead, str, str]`
- `AuthService.revoke_token(raw_token: str) -> None`
- `AuthService.get_user_by_id(user_id: UUID) -> UserRead | None`
- `hash_password(password: str) -> str`
- `verify_password(plain_password: str, hashed_password: str) -> bool`
- `create_access_token(user_id: UUID, email: str, settings: Settings) -> str`
- `decode_access_token(token: str, settings: Settings) -> dict[str, Any]`
- `create_refresh_token(user_id: UUID, email: str, settings: Settings) -> tuple[str, str]`
- `decode_refresh_token(token: str, settings: Settings) -> dict[str, Any]`
- `generate_csrf_token() -> str`
- `validate_csrf_token(header_token: str | None, cookie_token: str | None) -> bool`

