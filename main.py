from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
# from starlette.middleware.proxy import ProxyHeadersMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import engine, Base
from app.database import SessionLocal
from app.services.click_complate import deactivate_expired_premiums
from app.routers import auth_router, admin_router
from app.routers.photos import router as photos_router
# from app.routers.payment import router as payment_router
from app.routers.messages import router as messages_router

# from app.routers.sms import router as sms_router
from app.routers.translation import router as translation_router
from app.routers.user import router as user_router
from app.routers.employee import router as employee_router
from app.routers.salon import router as salon_router
from app.routers.appointments_router import router as appointment_router
from app.routers.schedules_router import router as schedule_router
from app.middleware.cors_proxy import CorsProxyMiddleware
from app.middleware.language import LanguageMiddleware
from app.routers.salon_mobile import router as mobile_router
from app.routers.mobile_defaults import router as mobile_defaults_router
from app.routers.city import router as city_router
from app.routers.mobile_employees import router as mobile_employees_router
from app.routers.mobile_schedules import router as mobile_schedules_router
from app.routers.comments import router as comments_router
from app.routers.mobile_noitf import router as mobile_notifications_router
from app.routers.history import router as history_router
from app.routers.click import router as click_router
from app.routers.ws_chat import router as ws_chat_router



# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    try:
        Base.metadata.create_all(bind=engine)
        print("Database tables created")
    except Exception as e:
        print(f"[Startup] Skipping table creation due to DB error: {e}")
    # Ensure default superadmin exists after tables are created
    try:
        from app import check_and_create_admin
        check_and_create_admin()
    except Exception:
        # Avoid breaking startup if admin creation fails
        pass

    # APScheduler: deactivate expired premiums periodically
    try:
        scheduler = BackgroundScheduler(timezone="UTC")

        def _deactivate_job():
            db = SessionLocal()
            try:
                count = deactivate_expired_premiums(db)
                if count:
                    print(f"[Scheduler] Deactivated {count} expired premium(s)")
            finally:
                try:
                    db.close()
                except Exception:
                    pass

        # Run daily at 00:00 (UTC) and also at app startup once
        _deactivate_job()
        scheduler.add_job(_deactivate_job, CronTrigger(hour=0, minute=0))
        scheduler.start()
        app.state.scheduler = scheduler
    except Exception as e:
        print(f"[Startup] Failed to start APScheduler: {e}")
    yield
    # Shutdown
    try:
        sched = getattr(app.state, "scheduler", None)
        if sched:
            sched.shutdown(wait=False)
    except Exception:
        pass


app = FastAPI(
    title="Freya Salon Backend API",
    description="""
    ## Freya Beauty Salon Management System API
    
    Bu API Freya go'zallik saloni boshqaruv tizimi uchun yaratilgan.
    
    ### Asosiy funksiyalar:
    - 🔐 **Autentifikatsiya va avtorizatsiya** (JWT token)
    - 👥 **Foydalanuvchilar boshqaruvi** (Admin, User, Employee)
    - 🏢 **Salon boshqaruvi** (Salon ma'lumotlari, xizmatlar)
    - 📅 **Vaqt jadvali boshqaruvi** (Booking, Schedule)
    - 💳 **To'lov tizimi** (Click.uz integratsiyasi)
    - 📱 **SMS xabarnomalar** (Eskiz.uz integratsiyasi)
    - 🌐 **Tarjima xizmati** (Gogletrans API)
    
    ### Texnologiyalar:
    - **FastAPI** - Web framework
    - **SQLAlchemy** - ORM
    - **MySQL** - Database
    - **JWT** - Authentication
    - **Pydantic** - Data validation
    
    ### Versiya: 2.0.0
    """,
    version="2.0.0",
    docs_url=None,  # Disable default docs
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
    contact={
        "name": "Freya Development Team",
        "email": "dev@freya.uz",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {"url": "http://localhost:8000", "description": "Development server"},
        {"url": "https://api.freyapp.uz", "description": "Production server"},
    ],
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
    debug=True
)

# Disable automatic slash redirects to avoid 307 scheme changes behind proxies
# try:
#     app.router.redirect_slashes = False
# except Exception:
#     pass

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://www.freyapp.uz",
    "https://freyapp.uz",
    "https://api.freyapp.uz",
    "https://freya-admin-frontend.vercel.app",
    "https://freya-admin-frontend-git-main-muhammadbekdev.vercel.app",
    "https://freya-admin-frontend-muhammadbekdev.vercel.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middlewares
app.add_middleware(CorsProxyMiddleware)
app.add_middleware(LanguageMiddleware)

# Respect X-Forwarded-* headers from reverse proxy and enforce HTTPS
# app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(HTTPSRedirectMiddleware)

# Add trusted host middleware for production
if os.getenv("NODE_ENV") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "api.freyapp.uz",
            "freyapp.uz",
            "www.freyapp.uz",
            "localhost",
            "127.0.0.1",
        ],
    )

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(user_router)
app.include_router(employee_router, prefix="/api")
app.include_router(salon_router, prefix="/api")
# app.include_router(payment_router, prefix="/api")
app.include_router(appointment_router, prefix="/api")
app.include_router(schedule_router, prefix="/api")
# app.include_router(sms_router, prefix="/api")
app.include_router(translation_router, prefix="/api")
app.include_router(photos_router, prefix="/api")
app.include_router(mobile_router, prefix="/api")
app.include_router(mobile_defaults_router, prefix="/api")
app.include_router(mobile_employees_router, prefix="/api")
app.include_router(mobile_schedules_router, prefix="/api")
app.include_router(messages_router, prefix="/api")
app.include_router(city_router, prefix="/api")
app.include_router(comments_router, prefix="/api")
app.include_router(mobile_notifications_router, prefix="/api")
app.include_router(history_router, prefix="/api")

app.include_router(click_router, prefix="/api")

# WebSocket chat router (separate endpoint)
app.include_router(ws_chat_router)


# Static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")
app.mount("/api/photos/", StaticFiles(directory="photos"), name="photos")

# Custom docs endpoint with unpkg.com CDN
@app.get("/api/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=app.title + " - Swagger UI",
        swagger_js_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://unpkg.com/swagger-ui-dist@5.9.0/swagger-ui.css",
    )


@app.get("/")
async def root():
    return {
        "message": "Freya Backend API is running",
        "environment": os.getenv("NODE_ENV", "development"),
        "port": os.getenv("PORT", "8000"),
        "database": "configured",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "freya-backend"}

# Global exception handlers to ensure JSON responses
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    try:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
