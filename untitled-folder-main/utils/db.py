import sqlite3
import os
import json
from datetime import datetime
from config import Config

def get_db_connection():
    """Get SQLite database connection with row factory"""
    db_path = Config.DATABASE_PATH
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_type TEXT NOT NULL, -- 'farmer' or 'customer'
            name TEXT NOT NULL,
            phone TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            location TEXT,
            district TEXT,
            aadhaar_masked TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # OTP sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT NOT NULL,
            session_id TEXT NOT NULL,
            otp_code TEXT,
            is_verified INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Recommendation history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS recommendation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            phone TEXT,
            district TEXT NOT NULL,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            planting_date TEXT NOT NULL,
            weather_summary TEXT,
            recommended_crops TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_by_phone(phone: str):
    """Retrieve user record by phone number"""
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE phone = ?', (phone,)).fetchone()
    conn.close()
    return dict(user) if user else None

def register_user(user_type: str, name: str, phone: str, password_hash: str, location: str = "", district: str = "", aadhaar_masked: str = ""):
    """Create a new user record"""
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO users (user_type, name, phone, password_hash, location, district, aadhaar_masked)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (user_type, name, phone, password_hash, location, district, aadhaar_masked))
        conn.commit()
        return True, "User registered successfully"
    except sqlite3.IntegrityError:
        return False, "Phone number is already registered"
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def save_otp_session(phone: str, session_id: str, otp_code: str = None):
    """Save an OTP session"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO otp_sessions (phone, session_id, otp_code, is_verified)
        VALUES (?, ?, ?, 0)
    ''', (phone, session_id, otp_code))
    conn.commit()
    conn.close()

def get_latest_otp_session(phone: str):
    """Get the latest OTP session for a phone number"""
    conn = get_db_connection()
    session = conn.execute('''
        SELECT * FROM otp_sessions 
        WHERE phone = ? 
        ORDER BY id DESC LIMIT 1
    ''', (phone,)).fetchone()
    conn.close()
    return dict(session) if session else None

def verify_otp_session(phone: str):
    """Mark the latest OTP session as verified"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE otp_sessions 
        SET is_verified = 1 
        WHERE id = (
            SELECT id FROM otp_sessions 
            WHERE phone = ? 
            ORDER BY id DESC LIMIT 1
        )
    ''', (phone,))
    conn.commit()
    conn.close()

def is_phone_verified(phone: str) -> bool:
    """Check if the latest OTP session for phone was verified within last 30 minutes"""
    conn = get_db_connection()
    session = conn.execute('''
        SELECT is_verified, created_at FROM otp_sessions 
        WHERE phone = ? 
        ORDER BY id DESC LIMIT 1
    ''', (phone,)).fetchone()
    conn.close()
    if session and session['is_verified'] == 1:
        return True
    return False

def save_recommendation_history(phone: str, district: str, lat: float, lon: float, date: str, weather_summary: dict, top_crops: list):
    """Log recommendation event to database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO recommendation_history (phone, district, latitude, longitude, planting_date, weather_summary, recommended_crops)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            phone or "Anonymous",
            district,
            lat,
            lon,
            date,
            json.dumps(weather_summary),
            json.dumps(top_crops)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to log recommendation history: {e}")

# Automatically ensure tables exist on module load
try:
    init_db()
except Exception as e:
    print(f"[DB] init_db warning: {e}")
