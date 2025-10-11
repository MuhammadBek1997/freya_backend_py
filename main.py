from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import auth_router, admin_router
from app.routers.photos import router as photos_router
from app.routers.payment import router as payment_router
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



# Load environment variables
load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created")
    # Ensure default superadmin exists after tables are created
    try:
        from app import check_and_create_admin
        check_and_create_admin()
    except Exception:
        # Avoid breaking startup if admin creation fails
        pass
    yield
    # Shutdown
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
        {
            "url": "https://freya-salon-backend-cc373ce6622a.herokuapp.com",
            "description": "Production server",
        },
    ],
    swagger_ui_parameters={"syntaxHighlight.theme": "obsidian"},
    debug=True
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://freya-admin-frontend.vercel.app",
    "https://freya-admin-frontend-git-main-muhammadbekdev.vercel.app",
    "https://freya-admin-frontend-muhammadbekdev.vercel.app",
    "https://freya-salon-backend-cc373ce6622a.herokuapp.com",
    "https://freya-salon-backend.herokuapp.com",
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

# Add trusted host middleware for production
if os.getenv("NODE_ENV") == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=[
            "freya-salon-backend-cc373ce6622a.herokuapp.com",
            "*.herokuapp.com",
        ],
    )

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(user_router)
app.include_router(employee_router, prefix="/api")
app.include_router(salon_router, prefix="/api")
app.include_router(payment_router, prefix="/api")
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


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
