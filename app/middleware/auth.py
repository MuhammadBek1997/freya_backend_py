# Re-export auth dependencies for backward compatibility
from app.auth.dependencies import (
    get_current_user,
    get_current_admin,
    get_current_superadmin,
    get_current_user_only,
    get_current_user_token,
    get_current_user_optional
)

__all__ = [
    "get_current_user",
    "get_current_admin", 
    "get_current_superadmin",
    "get_current_user_only",
    "get_current_user_token",
    "get_current_user_optional"
]