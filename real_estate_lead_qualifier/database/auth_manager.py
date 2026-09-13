import pandas as pd
import os
import hashlib
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_CSV = os.path.join(DATA_DIR, "users.csv")

USERS_COLUMNS = [
    "user_id", "name", "phone", "email", "password_hash", "salt", "role", "created_at"
]

def load_users() -> pd.DataFrame:
    try:
        df = pd.read_csv(USERS_CSV)
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=USERS_COLUMNS)

def save_users(df: pd.DataFrame):
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(USERS_CSV, index=False)

def hash_password(password: str, salt: str) -> str:
    """Hash a password using SHA-256 and a salt."""
    return hashlib.sha256((password + salt).encode('utf-8')).hexdigest()

def create_user(name: str, phone: str, email: str, password: str, role: str = "BUYER") -> tuple[bool, str]:
    """Create a new user. Returns (success, message)."""
    df = load_users()
    email = email.lower().strip()
    
    # Check duplicate email
    if not df.empty and email in df["email"].str.lower().str.strip().values:
        return False, "An account with this email already exists."
        
    user_id = f"U{(len(df) + 1):03d}"
    salt = os.urandom(16).hex()
    hashed_pw = hash_password(password, salt)
    
    new_user = {
        "user_id": user_id,
        "name": name,
        "phone": phone,
        "email": email,
        "password_hash": hashed_pw,
        "salt": salt,
        "role": role,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    df = pd.concat([df, pd.DataFrame([new_user])], ignore_index=True)
    save_users(df)
    return True, "Account created successfully."

def authenticate_user(email: str, password: str) -> dict:
    """Authenticate a user. Returns dict with user details if successful, else None."""
    df = load_users()
    if df.empty:
        return None
        
    email = email.lower().strip()
    user_row = df[df["email"].str.lower().str.strip() == email]
    
    if user_row.empty:
        return None
        
    user = user_row.iloc[0]
    salt = str(user["salt"])
    expected_hash = str(user["password_hash"])
    
    if hash_password(password, salt) == expected_hash:
        return {
            "user_id": user["user_id"],
            "name": user["name"],
            "role": user["role"]
        }
    return None

def ensure_default_broker():
    """Ensure a default broker account exists for testing and admin access."""
    df = load_users()
    broker_email = "broker@admin.com"
    if df.empty or broker_email not in df["email"].values:
        create_user(
            name="Admin Broker",
            phone="9999999999",
            email=broker_email,
            password="admin",
            role="BROKER"
        )
