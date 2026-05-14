from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from datetime import datetime
import subprocess
import sys
import requests

app = Flask(__name__)
CORS(app)

# ------------------ CONFIG ------------------ #
TWO_FACTOR_API_KEY = "7be799a1-5e26-11f0-a562-0200cd936042"
otp_sessions = {}
registered_customers = {}
registered_farmers = {}

# ------------------ BASIC ROUTES ------------------ #

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/market')
def market():
    return render_template('market.html')

@app.route('/farmer')
def farmer():
    return render_template('farmer.html')

@app.route('/customer')
def customer():
    return render_template('customer.html')

# ------------------ OTP ROUTES ------------------ #

@app.route('/send_otp', methods=['POST'])
def send_otp():
    phone = request.json.get("phone")
    if not phone or len(phone) != 10 or not phone.isdigit():
        return jsonify({"success": False, "error": "Invalid phone"}), 400

    try:
        url = f"https://2factor.in/API/V1/{TWO_FACTOR_API_KEY}/SMS/{phone}/AUTOGEN"
        res = requests.get(url).json()
        print("Send OTP:", res)

        if res.get("Status") == "Success":
            otp_sessions[phone] = res.get("Details")
            return jsonify({"success": True})
        else:
            return jsonify({"success": False, "error": res.get("Details")})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    phone = request.json.get("phone")
    otp = request.json.get("otp")
    session_id = otp_sessions.get(phone)

    if not session_id:
        return jsonify({"verified": False, "error": "Session not found"}), 400

    try:
        url = f"https://2factor.in/API/V1/{TWO_FACTOR_API_KEY}/SMS/VERIFY/{session_id}/{otp}"
        res = requests.get(url).json()
        print("Verify OTP:", res)

        if res.get("Status") == "Success" and res.get("Details") == "OTP Matched":
            return jsonify({"verified": True})
        else:
            return jsonify({"verified": False, "error": res.get("Details")})
    except Exception as e:
        return jsonify({"verified": False, "error": str(e)})

# ------------------ AUTH ROUTES ------------------ #

@app.route('/register_customer', methods=['POST'])
def register_customer():
    data = request.json
    phone = data.get("phone")
    if phone in registered_customers:
        return jsonify({"success": False, "error": "Already registered"}), 409

    registered_customers[phone] = {
        "first": data.get("first"),
        "last": data.get("last"),
        "password": data.get("password")
    }
    return jsonify({"success": True, "message": "Customer registered"})

@app.route('/login_customer', methods=['POST'])
def login_customer():
    data = request.json
    user = registered_customers.get(data.get("phone"))
    if user and user["password"] == data.get("password"):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

@app.route('/register_farmer', methods=['POST'])
def register_farmer():
    data = request.json
    phone = data.get("phone")
    if phone in registered_farmers:
        return jsonify({"success": False, "error": "Already registered"}), 409

    registered_farmers[phone] = {
        "name": data.get("name"),
        "aadhaar": data.get("aadhaar"),
        "location": data.get("location"),
        "password": data.get("password")
    }
    return jsonify({"success": True, "message": "Farmer registered"})

@app.route('/login_farmer', methods=['POST'])
def login_farmer():
    data = request.json
    user = registered_farmers.get(data.get("phone"))
    if user and user["password"] == data.get("password"):
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Invalid credentials"}), 401

# ------------------ MARKET RECOMMENDATION ------------------ #

@app.route('/get_recommendation', methods=['POST'])
def get_recommendation():
    print("Received request for recommendation")
    data = request.json

    latitude = data.get('latitude')
    longitude = data.get('longitude')
    district = data.get('district')

    if not (latitude and longitude and district):
        return jsonify({'error': 'Missing latitude, longitude, or district'}), 400

    current_date = datetime.now().strftime('%Y-%m-%d')

    try:
        result = subprocess.check_output([
            sys.executable, 'market_integrated.py',
            str(latitude), str(longitude), str(district), str(current_date)
        ], universal_newlines=True)

        print("Result from market_integrated.py:\n", result)
        return jsonify({'result': result})

    except Exception as e:
        print("Error running market_integrated.py:", e)
        return jsonify({'error': str(e)}), 500

# ------------------ RUN APP ------------------ #

if __name__ == '__main__':
    app.run(debug=True)
