"""
Authentication Endpoints

Login, signup, and session management for medical scribe users.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
import bcrypt
import secrets
from datetime import datetime, timedelta
from typing import Optional

from src.core.database import get_db
from src.models.user import User, UserRole
import structlog

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = structlog.get_logger(__name__)

# In-memory session store (use Redis in production)
sessions = {}

class SignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    role: UserRole = UserRole.PHYSICIAN

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    user_id: str
    username: str
    email: str
    full_name: Optional[str]
    role: str
    session_token: str

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_session_token() -> str:
    """Generate secure session token"""
    return secrets.token_urlsafe(32)

@router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Register a new user account
    """
    # Check if username exists
    existing_user = db.query(User).filter(User.username == request.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Check if email exists
    existing_email = db.query(User).filter(User.email == request.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    user = User(
        id=f"usr_{secrets.token_hex(8)}",
        username=request.username,
        email=request.email,
        password_hash=hash_password(request.password),
        full_name=request.full_name,
        role=request.role,
        is_active=True,
        is_verified=True,  # Set to False in production with email verification
        failed_login_attempts=0
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Create session
    session_token = create_session_token()
    sessions[session_token] = {
        "user_id": user.id,
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    
    logger.info("User registered", user_id=user.id, username=user.username)
    
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        session_token=session_token
    )

@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with username and password
    """
    # Find user
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check if account is locked
    if user.locked_until and user.locked_until > datetime.utcnow():
        raise HTTPException(status_code=423, detail="Account is locked. Try again later.")
    
    # Verify password
    if not verify_password(request.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.locked_until = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Check if account is active
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is deactivated")
    
    # Reset failed attempts and update last login
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create session
    session_token = create_session_token()
    sessions[session_token] = {
        "user_id": user.id,
        "expires_at": datetime.utcnow() + timedelta(days=7)
    }
    
    logger.info("User logged in", user_id=user.id, username=user.username)
    
    return AuthResponse(
        user_id=user.id,
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        role=user.role.value,
        session_token=session_token
    )

@router.post("/logout")
async def logout(session_token: str):
    """
    Logout and invalidate session
    """
    if session_token in sessions:
        user_id = sessions[session_token]["user_id"]
        del sessions[session_token]
        logger.info("User logged out", user_id=user_id)
    
    return {"message": "Logged out successfully"}

@router.get("/me")
async def get_current_user(session_token: str, db: Session = Depends(get_db)):
    """
    Get current user from session token
    """
    if session_token not in sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    
    session = sessions[session_token]
    
    # Check if session expired
    if session["expires_at"] < datetime.utcnow():
        del sessions[session_token]
        raise HTTPException(status_code=401, detail="Session expired")
    
    # Get user
    user = db.query(User).filter(User.id == session["user_id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value
    }
