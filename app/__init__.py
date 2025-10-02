# Freya Backend Python Package
import os
if not os.path.exists("uploads"):
    os.mkdir("uploads")

def check_and_create_admin():
    # Import inside function to avoid side effects at package import time
    from app.auth.jwt_utils import JWTUtils
    from app.database import SessionLocal
    db = SessionLocal()
    from app.models.admin import Admin
    from app.config import settings
    admin = db.query(Admin).filter(Admin.role == "superadmin").first()
    if not admin:
        admin_user = Admin(
            email=settings.SUPERADMIN_EMAIL,
            password_hash=JWTUtils.hash_password(settings.SUPERADMIN_PASSWORD),
            username=settings.SUPERADMIN_USERNAME,
            full_name=settings.SUPERADMIN_FIRST_NAME,
            phone=settings.SUPERADMIN_PHONE,
            is_active=True,
            role="superadmin",
        )
        db.add(admin_user)
        db.commit()
        print(
            f"Admin user created with email: {settings.SUPERADMIN_EMAIL} and password: {settings.SUPERADMIN_PASSWORD}"
        )
    db.close()

# Note: Do NOT call check_and_create_admin() at import time.
# It should be invoked explicitly during application startup after tables exist.