import bcrypt
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
from dotenv import load_dotenv

load_dotenv()

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# AES-256 encryption for API keys
ENCRYPTION_KEY = os.getenv("API_KEY_ENCRYPTION_KEY")
if not ENCRYPTION_KEY:
    # Generate a default key for development (32 bytes = 256 bits)
    ENCRYPTION_KEY = base64.b64encode(os.urandom(32)).decode()
    print(f"WARNING: Using generated encryption key. Set API_KEY_ENCRYPTION_KEY in .env for production")

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """Decode and verify a JWT access token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

def encrypt_api_key(plaintext: str) -> str:
    """Encrypt an API key using AES-256-GCM"""
    if not plaintext:
        return ""
    
    key = base64.b64decode(ENCRYPTION_KEY)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    # Combine nonce + ciphertext and base64 encode
    encrypted = base64.b64encode(nonce + ciphertext).decode("utf-8")
    return encrypted

def decrypt_api_key(encrypted: str) -> str:
    """Decrypt an API key using AES-256-GCM"""
    if not encrypted:
        return ""
    
    try:
        key = base64.b64decode(ENCRYPTION_KEY)
        raw = base64.b64decode(encrypted)
        nonce, ciphertext = raw[:12], raw[12:]
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception as e:
        print(f"ERROR: Failed to decrypt API key: {str(e)}")
        return ""
