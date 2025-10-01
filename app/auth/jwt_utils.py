"""
JWT utilities for authentication
"""
import jwt
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status
from app.config import settings


class JWTUtils:
    """JWT token utilities"""
    
    @staticmethod
    def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        
        # Set expiration time
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=7)  # Default 7 days
        
        # Add timestamp and unique identifiers
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        random_suffix = secrets.token_urlsafe(10)
        
        # Add user type prefix to ensure uniqueness
        user_type_prefix = {
            'superadmin': 'SA',
            'admin': 'AD',
            'employee': 'EM',
            'user': 'US'
        }.get(data.get('role', ''), 'UN')
        
        # Enhanced payload with unique identifiers
        to_encode.update({
            'exp': expire,
            'iat': datetime.utcnow(),
            'tokenId': f"{user_type_prefix}_{data.get('id')}_{timestamp}_{random_suffix}",
            'userType': data.get('role'),
            'sessionId': f"{user_type_prefix}_{timestamp}_{secrets.token_urlsafe(8)}"
        })
        
        encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def verify_token(token: str) -> Dict[str, Any]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token muddati tugagan"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token yaroqsiz"
            )
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return hashlib.sha256(plain_password.encode()).hexdigest() == hashed_password