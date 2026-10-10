# CodeAlpha_appcodevuln

This is a small user-authentication backend: a Flask REST API where people can register, log in, view profiles, and where admins get a protected area. It stores users in a SQLite file and exchanges JSON. There’s no frontend, so you’d test it with curl, Postman or a separate client.

# How it’s put together

Everything lives in one file. At startup it reads two environment variables: SECRET_KEY, which signs the session cookie and is required (the app refuses to start without it), and optionally DB_PATH, the location of the SQLite file. It then configures the session cookie to be HttpOnly (JavaScript can’t read it) and SameSite=Lax (limits cross-site request forgery).

# Where it came from

The first version you pasted was a deliberately vulnerable app: SQL injection via f-strings, MD5 hashing, hardcoded secrets, leaked password hashes and a hardcoded admin username check. The two versions after it are progressively hardened. The last one fixes all of those with parameterized queries, bcrypt, env-based secrets and DB-backed roles.

What’s missing to actually run it

The code assumes a users table with username, password, role and email columns, but nothing creates it. You’d need an init step, or to create the table by hand. After that, run it with something like SECRET_KEY=<long random string> python app.py.

The remaining issues I listed last time, such as the cookie Secure flag failing open, type errors becoming 500s and the lack of rate limiting, are the gap between this and something production-ready. I can write the table setup and patch those if you want a version that runs end to end.

# Here’s how to run your version (the bcrypt one) from scratch.

1. Install dependencies

bash
pip install flask bcrypt

2. Create the database table

The app doesn’t create it, so do this once in the project folder:

bash
python - <<'EOF'
import sqlite3
conn = sqlite3.connect("users.db")
conn.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password BLOB NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    email TEXT
)
""")
conn.commit()
EOF

3. Start the server

Save your code as app.py, then:

bash
# macOS/Linux
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
python app.py

# Windows PowerShell
$env:SECRET_KEY = python -c "import secrets; print(secrets.token_hex(32))"
python app.py

It listens on http://127.0.0.1:5000.

4. Try the endpoints with curl

The -c and -b flags save and send the session cookie, so you stay logged in between calls.

bash
# Register
curl -X POST http://127.0.0.1:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"strongpass123","email":"alice@example.com"}'

# Log in (saves the cookie to cookies.txt)
curl -X POST http://127.0.0.1:5000/login -c cookies.txt \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"strongpass123"}'

# View your own profile
curl http://127.0.0.1:5000/user/alice -b cookies.txt

# Admin area (returns 403 for a normal user)
curl http://127.0.0.1:5000/admin -b cookies.txt

# Log out
curl -X POST http://127.0.0.1:5000/logout -b cookies.txt

5. Make someone an admin

There’s no endpoint for this by design, so promote a user directly in the database, then log in again:

bash
sqlite3 users.db "UPDATE users SET role='admin' WHERE username='alice';"

After that, /admin returns the sensitive data and /user/<anyone> works for any username.

Common problems

RuntimeError: SECRET_KEY environment variable is required: you skipped the export in step 3, or set it in a different terminal.
no such table: users: step 2 wasn’t run in the same folder as the app.
401 Unauthorized: you forgot -b cookies.txt, or logged in with a different cookie file.
