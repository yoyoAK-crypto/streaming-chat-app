from passlib.context import CryptContext  # handles password hashing
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError  # creates and checks JWT tokens
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv

# Load SECRET_KEY from .env. It's used to sign tokens, so anyone who knows it can create valid tokens. Keep it private.
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")

# Stop the server at startup if the key is missing, instead of failing later on the first login
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY is not set in .env")

# bcrypt is a slow-on-purpose hashing algorithm, which makes guessing passwords expensive.
# deprecated="auto" lets old hash formats still be checked if you switch algorithms later.
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"  # how the token is signed: HMAC with SHA-256, using SECRET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES = 30  # after this, the user has to log in again

# Reads the "Authorization: Bearer <token>" header from each request.
# If the header is missing, FastAPI rejects the request before our code runs.
security = HTTPBearer()


# Turn a plain password into a hash to store in the database.
# The same password gives a different hash each time (bcrypt adds a random "salt"),
# and the hash can't be turned back into the password.
def hash_password(password: str) -> str:
    return pwd_context.hash(password)


# Check a login attempt: hash the typed password the same way and compare it with the stored hash.
# Returns True or False. The real password is never stored or compared directly.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# Build a signed token after a successful login. `data` is the payload, e.g. {"sub": "youssef"}.
def create_access_token(data: dict):
    to_encode = data.copy()  # copy so we don't change the caller's dict
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})  # "exp" is the standard JWT field for the expiry time
    # Sign the payload with SECRET_KEY. The result is the long "xxxxx.yyyyy.zzzzz" token string.
    # Anyone can read the payload, but changing it breaks the signature.
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# Used as Depends(get_current_user) on protected routes. It runs before the route and either
# returns the logged-in username or stops the request with a 401.
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials  # the token part of "Bearer <token>"
    credentials_exception = HTTPException(status_code=401, detail="Could not validate credentials")
    try:
        # Check the signature and the expiry. If the token was edited, signed with another key,
        # or has expired, this raises JWTError.
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")  # "sub" (subject) holds who the token belongs to
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username


# Quick manual check. Runs only with `python auth.py`, not when another file imports this one.
if __name__ == "__main__":
    hashed = hash_password("mypassword123")
    print(hashed)
    print(verify_password("mypassword123", hashed))  # True
    print(verify_password("wrongpassword", hashed))  # False

    token = create_access_token({"sub": "youssef"})
    print(token)
