# Secure Authentication Lab

A beginner-friendly local Flask authentication service for the Cyber Security milestone.

## Requirements
- Python 3.10 or newer
- VS Code (optional)
- Internet only for the first dependency installation

## Run on Windows (PowerShell)
Open this folder in VS Code, then run:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
$env:SECRET_KEY = py -c "import secrets; print(secrets.token_hex(32))"
py app.py
```

If PowerShell blocks virtual-environment activation, run the install and app commands using `py -m pip ...` and `py app.py` without activating, or use Command Prompt:
```bat
py -m venv .venv
.venv\\Scripts\\activate.bat
py -m pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000 in your browser. Create a test account, sign in, view the protected dashboard, and sign out.

## Run tests
```powershell
py -m pytest -q
```

The tests cover valid login, generic invalid-login errors, protected routes, logout, password validation and cookie security flags. The live rate limiter is enabled in the app; its timing behavior should be manually checked by making more than five failed login attempts within one minute in your own local test environment.

## Security controls implemented
- Passwords hashed with Werkzeug's scrypt password-hashing implementation.
- Server-side validation of usernames and password length.
- Parameterized SQLite statements.
- Login and registration rate limits using Flask-Limiter.
- Generic login error message for unknown usernames and incorrect passwords.
- Flask signed session cookie; only the user ID is stored in the session.
- Session cleared on successful login (session-fixation mitigation) and logout.
- HttpOnly, SameSite=Lax cookie flags; Secure cookie flag is configurable.
- Permanent session lifetime of 20 minutes.
- Protected dashboard checks the session user ID against the database on each request.
- Request body size limit.

## Important deployment notes
This is a learning lab, not a production-ready identity provider.
- `SECRET_KEY` must be a strong random secret and must never be committed to Git.
- `COOKIE_SECURE=1` must be used when deployed behind correctly configured HTTPS. It is `0` by default only so local HTTP testing works.
- Flask's default session is a signed client-side cookie, not an encrypted server-side session. Do not store secrets or sensitive personal data in it. For higher-assurance production use, consider a server-side session store and a mature identity provider.
- Flask-Limiter's default `memory://` storage is suitable only for local single-process testing. Use Redis or another shared storage backend for multi-worker deployment.
- Add CSRF protection (for example Flask-WTF), HTTPS/HSTS, monitoring, account recovery safeguards, and operational review before real deployment.
- Do not use real student passwords or personal data in this exercise.

## Repository contents
- `app.py` — Flask service and routes
- `templates/` — login, registration and dashboard pages
- `static/style.css` — interface styling
- `tests/test_auth.py` — automated tests
- `requirements.txt` — dependencies
- `.env.example` — configuration example (contains no real secret)
