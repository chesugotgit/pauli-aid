from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import bcrypt

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Database initialization
def init_db():
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      email TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL,
                      role TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS mood_entries
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      date TEXT NOT NULL,
                      mood TEXT NOT NULL,
                      FOREIGN KEY (user_id) REFERENCES users (id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS tasks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER,
                      task TEXT NOT NULL,
                      FOREIGN KEY (user_id) REFERENCES users (id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS articles
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      title TEXT NOT NULL,
                      content TEXT NOT NULL)''')
        conn.commit()

# Initialize the database
init_db()

# Helper function to hash passwords
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

# Helper function to check required fields
def check_required_fields(data, fields):
    for field in fields:
        if field not in data or not data[field]:
            return False
    return True

# Serve static files
@app.route('/')
def serve_index():
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# User registration
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    if not check_required_fields(data, ['name', 'email', 'password', 'role']):
        return jsonify({"error": "Missing required fields"}), 400

    hashed_password = hash_password(data['password'])

    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
                      (data['name'], data['email'], hashed_password, data['role']))
            conn.commit()
            return jsonify({"message": "User registered successfully"}), 201
        except sqlite3.IntegrityError:
            return jsonify({"error": "Email already exists"}), 400

# User login
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not check_required_fields(data, ['email', 'password']):
        return jsonify({"error": "Missing email or password"}), 400

    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, name, role, password FROM users WHERE email = ?", (data['email'],))
        user = c.fetchone()

    if user and bcrypt.checkpw(data['password'].encode(), user[3].encode()):
        return jsonify({"message": "Login successful", "user_id": user[0], "name": user[1], "role": user[2]}), 200
    else:
        return jsonify({"error": "Invalid email or password"}), 401

# Mood tracking
@app.route('/api/mood', methods=['POST'])
def track_mood():
    data = request.json
    if not check_required_fields(data, ['user_id', 'date', 'mood']):
        return jsonify({"error": "Missing required fields"}), 400

    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO mood_entries (user_id, date, mood) VALUES (?, ?, ?)",
                  (data['user_id'], data['date'], data['mood']))
        conn.commit()

    return jsonify({"message": "Mood tracked successfully"}), 201

@app.route('/api/mood/<int:user_id>', methods=['GET'])
def get_mood_history(user_id):
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("SELECT date, mood FROM mood_entries WHERE user_id = ? ORDER BY date DESC LIMIT 7", (user_id,))
        mood_history = c.fetchall()

    return jsonify(mood_history), 200

# Task management
@app.route('/api/tasks', methods=['POST'])
def add_task():
    data = request.json
    if not check_required_fields(data, ['user_id', 'task']):
        return jsonify({"error": "Missing required fields"}), 400

    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("INSERT INTO tasks (user_id, task) VALUES (?, ?)", (data['user_id'], data['task']))
        conn.commit()

    return jsonify({"message": "Task added successfully"}), 201

@app.route('/api/tasks/<int:user_id>', methods=['GET'])
def get_tasks(user_id):
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("SELECT id, task FROM tasks WHERE user_id = ?", (user_id,))
        tasks = c.fetchall()

    return jsonify(tasks), 200

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()

    return jsonify({"message": "Task deleted successfully"}), 200

# New routes for articles
@app.route('/api/articles', methods=['GET'])
def get_articles():
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("SELECT title, content FROM articles")
        articles = c.fetchall()
    return jsonify(articles), 200

@app.route('/api/articles/search', methods=['GET'])
def search_articles():
    query = request.args.get('query')
    with sqlite3.connect('pauli_aid.db') as conn:
        c = conn.cursor()
        c.execute("SELECT title, content FROM articles WHERE title LIKE ?", ('%' + query + '%',))
        articles = c.fetchall()
    return jsonify(articles), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)