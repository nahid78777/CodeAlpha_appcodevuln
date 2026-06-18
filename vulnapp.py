import sqlite3
import hashlib
import os
from flask import Flask, request, jsonify, session
app = Flask(__name__)
app.secret_key = "hardcoded_secret_key_123"  # Hardcoded secret key
DB_PASSWORD = "admin123"  # Hardcoded database password
def get_db_connection():
    conn = sqlite3.connect('users.db')
    return conn
@app.route('/register', methods=['POST'])
def register():
    username = request.json.get('username')
    password = request.json.get('password')
    # Uses MD5 for password hashing (weak cryptography)
    hashed = hashlib.md5(password.encode()).hexdigest()
    conn = get_db_connection()
    # SQL injection vulnerability: string concatenation
    conn.execute(f"INSERT INTO users (username, password) VALUES ('{username}', '{hashed}')")
    conn.commit()
    conn.close()
    return jsonify({"message": "User registered"})
@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    conn = get_db_connection()
    # SQL injection vulnerability
    cursor = conn.execute(
        f"SELECT * FROM users WHERE username = '{username}' "
        f"AND password = '{hashlib.md5(password.encode()).hexdigest()}'"
    )
    user = cursor.fetchone()
    conn.close()
    if user:
        session['username'] = username
        return jsonify({"message": "Login successful"})
    return jsonify({"error": "Invalid credentials"}), 401
@app.route('/user/<username>', methods=['GET'])
def get_user(username):
    # Missing authorization check: any logged-in user can view any profile
    if 'username' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    conn = get_db_connection()
    # SQL injection vulnerability
    cursor = conn.execute(f"SELECT * FROM users WHERE username = '{username}'")
    user = cursor.fetchone()
    conn.close()
    if user:
        # Information disclosure: returns password hash
        return jsonify({"username": user[0], "password": user[1]})
    return jsonify({"error": "User not found"}), 404
@app.route('/admin', methods=['GET'])
def admin_panel():
    # Hardcoded administrator check
    if session.get('username') == 'admin':
        return jsonify({"data": "Sensitive admin data"})
    return jsonify({"error": "Forbidden"}), 403
if __name__ == '__main__':
    app.run(debug=True)  # Debug mode enabled