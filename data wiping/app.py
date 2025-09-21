# app.py (Corrected with missing functions restored)

import os
import subprocess
import string
import sqlite3
import random
import time
import hashlib
import uuid
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from fpdf import FPDF
import qrcode
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

app = Flask(__name__)
app.secret_key = os.urandom(24)

# --- Configuration ---
C_EXECUTABLE_PATH = os.path.join('wipingEngine', 'wipeEngine.exe')
TEMP_DIR = os.path.join(app.root_path, 'temp_logs')
if not os.path.exists(TEMP_DIR):
    os.makedirs(TEMP_DIR)

# --- Twilio Configuration ---
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER')

if all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
    twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
else:
    print("\n--- TWILIO WARNING ---")
    print("Twilio environment variables are not set.")
    print("The application will run, but OTP via SMS will be disabled.")
    print("----------------------\n")
    twilio_client = None

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# --- Decorators for Route Protection (THE MISSING CODE) ---
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("You must be logged in to view this page.", "warning")
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def otp_verified_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('otp_verified'):
            flash("Please verify your identity with an OTP.", "warning")
            return redirect(url_for('send_otp'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('wipe_tool'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        if user and check_password_hash(user['password_hash'], password):
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['phone_number'] = user['phone_number']
            session['otp_verified'] = False
            flash(f"Welcome back, {user['username']}!", "info")
            return redirect(url_for('send_otp'))
        else:
            flash("Invalid username or password.", "danger")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        phone_number = request.form['phone_number']
        conn = get_db_connection()
        user_exists = conn.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone()
        if user_exists:
            flash("Username already exists.", "warning")
            conn.close()
            return redirect(url_for('signup'))
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash, phone_number) VALUES (?, ?, ?)', (username, password_hash, phone_number))
        conn.commit()
        conn.close()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/send-otp')
@login_required
def send_otp():
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    phone_number = session.get('phone_number')
    print(f"\nOTP for {session.get('username')}: {otp}\n")
    if twilio_client:
        try:
            twilio_client.messages.create(body=f"Your code is: {otp}", from_=TWILIO_PHONE_NUMBER, to=phone_number)
            flash("OTP sent to your phone.", "info")
        except TwilioRestException as e:
            flash("Could not send OTP via SMS.", "danger")
            flash("OTP is in server console as a fallback.", "warning")
    else:
        flash("OTP is in server console.", "warning")
    return redirect(url_for('verify_otp'))

@app.route('/verify-otp', methods=['GET', 'POST'])
@login_required
def verify_otp():
    if session.get('otp_verified'):
        return redirect(url_for('wipe_tool'))
    if request.method == 'POST':
        if 'otp' in session and session['otp'] == request.form['otp']:
            session['otp_verified'] = True
            session.pop('otp', None)
            flash("Verification successful!", "success")
            return redirect(url_for('wipe_tool'))
        else:
            flash("Invalid OTP.", "danger")
    return render_template('verify_otp.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# --- Main Application Routes ---
@app.route('/wipe-tool')
@login_required
@otp_verified_required
def wipe_tool():
    return render_template('wipe_tool.html')

@app.route('/browse')
@login_required
@otp_verified_required
def browse_fs():
    path = request.args.get('path', None)
    if not path:
        drives = [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]
        return jsonify({'current_path': '', 'folders': drives, 'files': []})
    try:
        items = os.listdir(path)
        folders = sorted([i for i in items if os.path.isdir(os.path.join(path, i))])
        files = sorted([i for i in items if not os.path.isdir(os.path.join(path, i))])
        parent_path = os.path.dirname(path) if len(path) > 3 else ''
        return jsonify({'current_path': path, 'parent_path': parent_path, 'folders': folders, 'files': files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/wipe', methods=['POST'])
@login_required
@otp_verified_required
def wipe_file_route():
    data = request.get_json()
    wipe_type = data.get('wipe_type')
    path = data.get('path')
    wipe_method = data.get('wipe_method')

    if not all([wipe_type, path, wipe_method]):
        return jsonify({'log': 'ERROR: Missing parameters.'}), 400
    if not os.path.exists(C_EXECUTABLE_PATH):
        return jsonify({'log': f"ERROR: Executable not found. Please compile the C code."}), 500

    log_output = ""
    temp_log_filename = os.path.join(TEMP_DIR, f"{uuid.uuid4()}.log")

    try:
        command = [C_EXECUTABLE_PATH, temp_log_filename, f'--{wipe_type}', path, wipe_method]
        process = subprocess.run(command, capture_output=True, check=False)
        
        if os.path.exists(temp_log_filename):
            with open(temp_log_filename, 'r', encoding='utf-16') as f:
                log_output = f.read()

        pdf_link = None
        if process.returncode == 0:
            # This is a simplified PDF generation. You can paste your full, detailed one back here.
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
            unique_id = str(uuid.uuid4())
            class PDF(FPDF):
                def header(self): self.set_font("Arial", 'B', 12); self.cell(0, 10, "Certificate of Data Sanitization", 0, 1, 'C')
                def footer(self): self.set_y(-15); self.set_font("Arial", 'I', 8); self.cell(0, 10, f"Page {self.page_no()}", 0, 0, 'C')
            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", '', 10)
            pdf.multi_cell(0, 8, f"Wipe Operation Successful\n\nTarget: {path}\nTimestamp: {timestamp}\n\n--- Execution Log ---\n{log_output}")
            pdf_filename = f"cert_{unique_id}.pdf"
            pdf_path = os.path.join('static', 'certificates', pdf_filename)
            pdf.output(pdf_path)
            pdf_link = url_for('static', filename=f'certificates/{pdf_filename}')

        return jsonify({'log': log_output, 'success': process.returncode == 0, 'pdf_link': pdf_link})
        
    except Exception as e:
        return jsonify({'log': f"A fatal Python error occurred: {str(e)}"}), 500
    finally:
        if os.path.exists(temp_log_filename):
            os.remove(temp_log_filename)
        
if __name__ == '__main__':
    if not os.path.exists('users.db'):
        print("ERROR: Database 'users.db' not found!")
    else:
        os.makedirs(os.path.join('static', 'certificates'), exist_ok=True)
        app.run(host='0.0.0.0', port=5000, debug=False)