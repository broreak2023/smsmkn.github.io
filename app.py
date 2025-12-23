import requests
import os
import sys  # Added sys to exit if passwords are missing
from flask import Flask, render_template, request, redirect, url_for, session
from dotenv import load_dotenv

# 1. Load secrets from .env
load_dotenv()

# ==========================================
#  🔒 SECURITY CHECK (STRICT)
# ==========================================
# We fetch the variables WITHOUT default values.
# If they are missing in .env, they will be None.
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

# Check if they exist. If not, STOP the app.
if not ADMIN_USERNAME or not ADMIN_PASSWORD or not FLASK_SECRET_KEY:
    print("❌ CRITICAL ERROR: Missing credentials in .env file!")
    print("   Please ensure ADMIN_USERNAME, ADMIN_PASSWORD, and FLASK_SECRET_KEY are set.")
    sys.exit(1) # Stop the program

# ==========================================
#  1. CONFIGURATION
# ==========================================
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

# --- API 1: STANDARD ---
API1_URL = os.getenv("API1_URL")
API1_CRED = {
    "username": os.getenv("API1_USERNAME"),
    "pass": os.getenv("API1_PASSWORD"),
    "sender": os.getenv("API1_SENDER"),
    "cd": os.getenv("API1_CD"),
    "int": os.getenv("API1_INT")
}

# --- API 2: SMPP/HTTP ---
API2_URL = os.getenv("API2_URL")
API2_CRED = {
    "username": os.getenv("API2_USERNAME"),
    "password": os.getenv("API2_PASSWORD"),
    "type": os.getenv("API2_TYPE")
}

# ==========================================
#  2. LOGIN ROUTES
# ==========================================
@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        user_input = request.form.get('username')
        pass_input = request.form.get('password')

        # Compare input against the variables loaded strictly from .env
        if user_input == ADMIN_USERNAME and pass_input == ADMIN_PASSWORD:
            session['logged_in'] = True
            session['username'] = user_input
            return redirect(url_for('dashboard'))
        else:
            error = "❌ Invalid Username or Password"

    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# ==========================================
#  3. DASHBOARD LOGIC (PROTECTED)
# ==========================================
@app.route('/', methods=['GET', 'POST'])
def dashboard():
    # 🔒 SECURITY CHECK
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    # --- IF USER SUBMITS FORM (POST) ---
    if request.method == 'POST':
        result = None
        res_type = ""
        active_tab = "api1"

        # --- HANDLE API 1 FORM ---
        if 'btn_api1' in request.form:
            active_tab = "api1"
            phone = request.form.get('phone')
            msg = request.form.get('message')
            
            payload = API1_CRED.copy()
            payload.update({"smstext": msg, "gsm": phone})
            
            try:
                r = requests.post(API1_URL, data=payload, timeout=10)
                response_text = r.text.lower()
                
                # Check for success indicators
                if r.status_code == 200 and ("success" in response_text or response_text.startswith("0") or "result=0" in response_text):
                    result = f"✅ API 1 Success: {r.text}"
                    res_type = "success"
                else:
                    result = f"⚠️ API 1 Error: {r.text}"
                    res_type = "danger"
            except Exception as e:
                result = f"❌ System Error: {e}"
                res_type = "danger"

        # --- HANDLE API 2 FORM ---
        elif 'btn_api2' in request.form:
            active_tab = "api2"
            to_num = request.form.get('to')
            sender = request.form.get('from')
            msg = request.form.get('message')
            gw = request.form.get('gateway')

            payload = {
                "username": API2_CRED['username'],
                "password": API2_CRED['password'],
                "message-type": API2_CRED['type'],
                "to": to_num,
                "from": sender,
                "message": msg,
                "gateway": gw
            }
            try:
                r = requests.post(API2_URL, data=payload, timeout=10)
                if r.status_code == 200:
                    result = f"✅ API 2 Success: {r.text}"
                    res_type = "success"
                else:
                    result = f"⚠️ API 2 Failed ({r.status_code}): {r.text}"
                    res_type = "danger"
            except Exception as e:
                result = f"❌ System Error: {e}"
                res_type = "danger"

        # Redirect to prevent form resubmission
        session['result'] = result
        session['res_type'] = res_type
        session['active_tab'] = active_tab
        return redirect(url_for('dashboard'))

    # --- IF USER LOADS PAGE (GET) ---
    result = session.pop('result', None)
    res_type = session.pop('res_type', "")
    active_tab = session.pop('active_tab', "api1")

    return render_template('index.html', result=result, res_type=res_type, active_tab=active_tab)

# ==========================================
#  4. MAIN LAUNCHER
# ==========================================
if __name__ == "__main__":
    print("🌍 Website starting at http://127.0.0.1:5000")
    app.run(debug=True, port=5000)