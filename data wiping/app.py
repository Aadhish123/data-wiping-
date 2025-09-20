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

app = Flask(__name__)
app.secret_key = os.urandom(24)

C_EXECUTABLE_PATH = os.path.join('wipingEngine', 'wipeEngine.exe')

# --- Helper Functions ---
def get_db_connection():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

def get_physical_disks():
    disks = []
    try:
        cmd = "wmic diskdrive get Index,Caption,Size /format:csv"
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        lines = result.stdout.strip().split('\n')
        for line in lines[2:]:
            if line:
                _, caption, index, size_str = line.strip().split(',')
                size_gb = float(size_str) / (1024**3)
                disk_path = f"\\\\.\\PhysicalDrive{index}"
                display_name = f"Disk {index}: {caption.strip()} ({size_gb:.2f} GB)"
                disks.append({'path': disk_path, 'name': display_name})
    except Exception as e:
        print(f"Could not get physical disks: {e}")
    return disks

# --- Decorators for Route Protection ---
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
            return redirect(url_for('verify_otp'))
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
            flash(f"Welcome back, {user['username']}!", "success")
            return redirect(url_for('verify_otp'))
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
            flash("Username already exists. Please choose another.", "warning")
            conn.close()
            return redirect(url_for('signup'))
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash, phone_number) VALUES (?, ?, ?)',
                     (username, password_hash, phone_number))
        conn.commit()
        conn.close()
        flash("Account created successfully! Please log in.", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/verify-otp', methods=['GET', 'POST'])
@login_required
def verify_otp():
    if request.method == 'POST':
        user_otp = request.form['otp']
        if 'otp' in session and session['otp'] == user_otp:
            session['otp_verified'] = True
            session.pop('otp', None)
            flash("Verification successful! Access granted.", "success")
            return redirect(url_for('wipe_tool'))
        else:
            flash("Invalid OTP. Please try again.", "danger")
    return render_template('verify_otp.html')

@app.route('/send-otp')
@login_required
def send_otp():
    otp = str(random.randint(100000, 999999))
    session['otp'] = otp
    phone_number = session.get('phone_number', 'N/A')
    print("\n" + "="*50)
    print(f"      OTP FOR USER: {session.get('username')}")
    print(f"      PHONE NUMBER: {phone_number}")
    print(f"      YOUR OTP IS: {otp}")
    print("="*50 + "\n")
    flash(f"An OTP has been sent to the console.", "info")
    return redirect(url_for('verify_otp'))

@app.route('/logout')
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
    wipe_type = request.args.get('type', 'file')
    if wipe_type == 'disk':
        disks = get_physical_disks()
        return jsonify({'disks': disks})
    path = request.args.get('path', None)
    drives = [f"{letter}:\\" for letter in string.ascii_uppercase if os.path.exists(f"{letter}:\\")]
    allowed_roots = [os.path.abspath(d) for d in drives]
    if not path:
        return jsonify({'current_path': '', 'folders': allowed_roots, 'files': []})
    requested_path = os.path.abspath(path)
    if not any(requested_path.startswith(root) for root in allowed_roots):
        return jsonify({"error": "Access denied."}), 403
    try:
        items = os.listdir(requested_path)
        folders = sorted([item for item in items if os.path.isdir(os.path.join(requested_path, item))])
        files = sorted([item for item in items if not os.path.isdir(os.path.join(requested_path, item))])
        parent_path = os.path.dirname(requested_path)
        if requested_path.rstrip('\\') in allowed_roots: parent_path = ''
        return jsonify({'current_path': requested_path, 'parent_path': parent_path, 'folders': folders, 'files': files})
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
        return jsonify({'stderr': 'ERROR: Missing parameters.'}), 400
    if not os.path.exists(C_EXECUTABLE_PATH):
        return jsonify({'stderr': f"ERROR: Executable not found. Please compile the C code."}), 500

    try:
        command = [C_EXECUTABLE_PATH, f'--{wipe_type}', path, wipe_method]
        process = subprocess.run(command, capture_output=True, text=True, check=False)
        log_output = process.stdout + process.stderr
        
        pdf_link = None
        if process.returncode == 0 and log_output:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S %Z")
            log_hash = hashlib.sha256(log_output.encode()).hexdigest()
            unique_id = str(uuid.uuid4())

            method_to_standard = {
                '--clear': 'NIST 800-88 Clear',
                '--purge': 'DoD 5220.22-M',
                '--destroy-sw': 'NIST 800-88 Purge (7-Pass Overwrite)'
            }
            standard = method_to_standard.get(wipe_method, 'Custom')
            
            serial_number = "N/A"
            if wipe_type == 'disk':
                for line in log_output.split('\n'):
                    if "Serial Number:" in line:
                        serial_number = line.split("Serial Number:")[1].strip()
                        break

            qr_data = f"Ref: {unique_id}\nTarget: {path}\nSHA256: {log_hash[:16]}..."
            qr_img = qrcode.make(qr_data)
            qr_filename = f"qr_{int(time.time())}.png"
            qr_path = os.path.join('static', 'qr_codes', qr_filename)
            qr_img.save(qr_path)
            
            class PDF(FPDF):
                def header(self):
                    self.set_font("Arial", 'B', 20)
                    self.cell(0, 10, "Zero Leaks", 0, 1, 'L')
                    self.set_font("Arial", '', 12)
                    self.cell(0, 10, "Certificate of Data Sanitization", 0, 1, 'L')
                    self.line(10, 30, 200, 30)
                    self.ln(10)
                
                def footer(self):
                    self.set_y(-15)
                    self.set_font("Arial", 'I', 8)
                    self.cell(0, 10, f"Page {self.page_no()}", 0, 0, 'C')

            pdf = PDF()
            pdf.add_page()
            pdf.set_font("Arial", '', 12)
            
            label_w = 55
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(label_w, 8, "Unique Reference Number:")
            pdf.set_font("Courier", '', 11)
            pdf.cell(0, 8, unique_id, 0, 1)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(label_w, 8, "Date and Time:")
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, timestamp, 0, 1)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(label_w, 8, "Description of Item:")
            pdf.set_font("Arial", '', 11)
            pdf.multi_cell(0, 8, path)

            if wipe_type == 'disk' and serial_number != 'N/A':
                pdf.set_font("Arial", 'B', 11)
                pdf.cell(label_w, 8, "Asset Serial Number:")
                pdf.set_font("Arial", '', 11)
                pdf.cell(0, 8, serial_number, 0, 1)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(label_w, 8, "Destruction Method:")
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, wipe_method, 0, 1)

            pdf.set_font("Arial", 'B', 11)
            pdf.cell(label_w, 8, "Compliance Standard:")
            pdf.set_font("Arial", '', 11)
            pdf.cell(0, 8, standard, 0, 1)
            
            pdf.image(qr_path, x=150, y=35, w=50)

            pdf.ln(20)
            pdf.set_font("Arial", '', 11)
            pdf.cell(95, 10, f"Technician: {session.get('username')}", 0, 0, 'L')
            pdf.cell(95, 10, "Witness Signature:", 0, 1, 'L')
            pdf.cell(95, 10, "Signature: ____________________", 0, 0, 'L')
            pdf.cell(95, 10, "____________________", 0, 1, 'L')

            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "Verification Details", 0, 1, 'L')
            pdf.ln(5)
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "SHA-256 Hash of Log:", 0, 1)
            pdf.set_font("Courier", '', 8)
            pdf.multi_cell(0, 5, log_hash)
            
            pdf.ln(5)
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, "Full Execution Log:", 0, 1)
            pdf.set_draw_color(200, 200, 200)
            pdf.rect(pdf.get_x(), pdf.get_y(), 190, 150, 'D')
            pdf.set_xy(pdf.get_x() + 2, pdf.get_y() + 2)
            pdf.set_font("Courier", '', 8)
            pdf.multi_cell(186, 5, log_output)

            pdf_filename = f"cert_{unique_id}.pdf"
            pdf_path = os.path.join('static', 'certificates', pdf_filename)
            pdf.output(pdf_path)
            pdf_link = url_for('static', filename=f'certificates/{pdf_filename}')

        return jsonify({'log': log_output, 'success': process.returncode == 0, 'pdf_link': pdf_link})
        
    except Exception as e:
        return jsonify({'stderr': f"An unexpected error occurred: {str(e)}"}), 500

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        print("ERROR: Database 'users.db' not found!")
        print("Please run 'python database.py' once to create it.")
    else:
        os.makedirs(os.path.join('static', 'certificates'), exist_ok=True)
        os.makedirs(os.path.join('static', 'qr_codes'), exist_ok=True)
        print("Starting Zero Leaks server...")
        print("Access the tool at http://127.0.0.1:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)