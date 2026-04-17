from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import users_collection
from bson import ObjectId
import bcrypt

SECRET_KEY = "workviser_secret_key_2024"
ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = 24

bearer = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash password using bcrypt directly"""
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    """Verify plain password against stored hash"""
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8")
    )

def create_token(data: dict) -> str:
    """Create JWT token"""
    payload = data.copy()
    expire = datetime.utcnow() + timedelta(hours=TOKEN_EXPIRE_HOURS)
    payload.update({"exp": expire})
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> dict:
    """Decode and validate JWT token"""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer)
):
    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token"
        )

    user = await users_collection.find_one(
        {"_id": ObjectId(payload.get("user_id"))}
    )

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found"
        )

    return user
### Explanation:

# SECRET_KEY
# - Secret phrase used to sign JWT tokens
# - Like a wax seal — proves token came from us
# - Never share or commit this to GitHub

# ALGORITHM = "HS256"
# - Encryption method for JWT
# - Industry standard, widely used

# TOKEN_EXPIRE_HOURS = 24
# - Token dies after 24 hours
# - User must login again after that

# pwd_context
# - Sets up bcrypt hashing engine
# - bcrypt is the strongest standard for password hashing

# bearer
# - Reads Authorization: Bearer <token> from request headers
# - Every protected route uses this automatically

# hash_password()
# 
# Input:  "test123"
# Output: "$2b$12$xK9...randomhash"
# 
# - One way — you can never reverse it back to "test123"

# verify_password()
# 
# Input:  plain="test123", hashed="$2b$12$xK9..."
# Output: True or False