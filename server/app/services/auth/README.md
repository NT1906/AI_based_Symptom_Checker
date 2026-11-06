# Authentication Service (`app.services.auth`)

Provides user registration, Argon2id password hashing, credential authentication, and signed JWT session token management.

## Responsibilities
- **Registration**: Registers new accounts, rejects duplicate emails with typed 409 Conflict errors, and securely hashes passwords with Argon2id before database storage.
- **Authentication**: Validates credentials using constant-time verification, mitigates user-enumeration timing attacks, and generates signed HS256 JWT access tokens.
- **Sanitization**: Strictly purges passwords and password hashes from API responses (`UserRead`).

## Security Invariants
- **Never Plaintext**: Plaintext passwords are never written to disk, database, or structlog logs.
- **Argon2id Parameters**: OWASP-compliant memory cost (64 MB), time cost (3), parallelism (4), and salt length (16 bytes).
- **Cookie Security**: Tokens are transported in `HttpOnly`, `SameSite=Lax` cookies, with `Secure=True` enforced in staging and production environments.

## Public Interface
- `AuthService.register_user(payload: UserRegisterRequest) -> UserRead`
- `AuthService.authenticate_user(payload: UserLoginRequest) -> tuple[UserRead, str]`
- `AuthService.get_user_by_id(user_id: UUID) -> UserRead | None`
- `hash_password(password: str) -> str`
- `verify_password(plain_password: str, hashed_password: str) -> bool`
- `create_access_token(user_id: UUID, email: str, settings: Settings) -> str`
- `decode_access_token(token: str, settings: Settings) -> dict[str, Any]`

