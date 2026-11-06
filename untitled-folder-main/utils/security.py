import re
from werkzeug.security import generate_password_hash, check_password_hash

def hash_password(password: str) -> str:
    """Hash password securely using Werkzeug PBKDF2/scrypt"""
    return generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)

def verify_password(stored_hash: str, provided_password: str) -> bool:
    """Verify password against stored hash"""
    if not stored_hash or not provided_password:
        return False
    return check_password_hash(stored_hash, provided_password)

def sanitize_phone(phone: str) -> str:
    """Sanitize and validate 10-digit Indian mobile number"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 10 and digits[0] in "56789":
        return digits
    return ""

def validate_coordinates(lat: float, lon: float) -> bool:
    """Validate that coordinates are within valid geographic range"""
    try:
        lat = float(lat)
        lon = float(lon)
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0
    except (ValueError, TypeError):
        return False

def mask_aadhaar(aadhaar: str) -> str:
    """Safely mask 12-digit Aadhaar number into XXXX-XXXX-1234 without storing plaintext"""
    if not aadhaar:
        return ""
    clean = re.sub(r'\D', '', str(aadhaar))
    if len(clean) >= 4:
        return f"XXXX-XXXX-{clean[-4:]}"
    return "XXXX-XXXX-XXXX"
