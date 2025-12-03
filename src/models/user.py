"""
User and Role Models

Authentication and authorization models for HIPAA-compliant access control.
"""

from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum as SQLEnum
from datetime import datetime
import enum

from src.models.base import Base, TimestampMixin


class UserRole(str, enum.Enum):
    """User roles for HIPAA-compliant access control"""
    ADMIN = "admin"
    PHYSICIAN = "physician"
    NURSE = "nurse"
    OFFICE_MANAGER = "office_manager"
    AUDITOR = "auditor"


class User(Base, TimestampMixin):
    """User account"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    full_name = Column(String(200), nullable=True)
    role = Column(SQLEnum(UserRole), default=UserRole.PHYSICIAN)
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    last_login = Column(DateTime, nullable=True)
    
    # Security
    mfa_enabled = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<User {self.username}>"
