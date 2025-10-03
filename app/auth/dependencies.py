"""
Authentication dependencies for FastAPI
"""
from typing import Optional, Union
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Admin, User, Employee
from app.auth.jwt_utils import JWTUtils
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Union[Admin, User, Employee]:
    """Get current authenticated user (any type)"""
    try:
        token = credentials.credentials
        payload = JWTUtils.verify_token(token)
        
        user_id = payload.get("id")
        role = payload.get("role")
        
        if not user_id or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token ma'lumotlari noto'g'ri"
            )
        
        # Check based on role
        if role in ['superadmin', 'admin', 'private_admin']:
            user = db.query(Admin).filter(
                Admin.id == user_id,
                Admin.is_active == True
            ).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Admin topilmadi yoki faol emas"
                )
            user.role = role  # Set role from token
            return user
            
        elif role == 'employee':
            # Authenticate using the actual Employee record
            employee = db.query(Employee).filter(
                Employee.id == user_id,
                Employee.is_active == True
            ).first()

            if not employee:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Xodim topilmadi yoki faol emas"
                )

            employee.role = 'employee'
            return employee
            
        else:  # user role
            user_id = payload.get("userId") or payload.get("id")
            user = db.query(User).filter(
                User.id == user_id,
                User.is_active == True
            ).first()
            
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Foydalanuvchi topilmadi yoki faol emas"
                )
            
            user.role = 'user'
            return user
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz"
        )


async def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current authenticated admin (admin or superadmin)"""
    try:
        token = credentials.credentials
        payload = JWTUtils.verify_token(token)
        
        user_id = payload.get("id")
        role = payload.get("role")
        
        if not user_id or role not in ['admin', 'superadmin', 'private_admin']:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin huquqi talab qilinadi"
            )
        
        admin = db.query(Admin).filter(
            Admin.id == user_id,
            Admin.is_active == True
        ).first()
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Admin topilmadi yoki faol emas"
            )
        
        admin.role = role  # Set role from token
        return admin
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Admin authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz"
        )


async def get_current_superadmin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Admin:
    """Get current authenticated superadmin"""
    try:
        token = credentials.credentials
        payload = JWTUtils.verify_token(token)
        
        user_id = payload.get("id")
        role = payload.get("role")
        
        if not user_id or role != 'superadmin':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Superadmin huquqi talab qilinadi"
            )
        
        admin = db.query(Admin).filter(
            Admin.id == user_id,
            Admin.role == 'superadmin',
            Admin.is_active == True
        ).first()
        
        if not admin:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Superadmin topilmadi yoki faol emas"
            )
        
        return admin
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Superadmin authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz"
        )


async def get_current_user_only(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user (only users, not admin/employee)"""
    try:
        token = credentials.credentials
        payload = JWTUtils.verify_token(token)
        
        user_id = payload.get("userId") or payload.get("id")
        role = payload.get("role")
        
        if role and role != 'user':
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Faqat foydalanuvchi huquqi bilan kirish mumkin"
            )
        
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Foydalanuvchi topilmadi yoki faol emas"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz"
        )


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user with readonly token verification"""
    try:
        token = credentials.credentials
        payload = JWTUtils.verify_token(token)
        
        token_type = payload.get("type")
        if token_type != "user_readonly":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Faqat user token bilan kirish mumkin"
            )
        
        user_id = payload.get("userId")
        user = db.query(User).filter(
            User.id == user_id,
            User.is_active == True
        ).first()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Foydalanuvchi topilmadi yoki faol emas"
            )
        
        return user
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"User token authentication error: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token yaroqsiz"
        )


# Optional authentication (for endpoints that work with or without auth)
async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[Union[Admin, User, Employee]]:
    """Get current user if token is provided, otherwise return None"""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None