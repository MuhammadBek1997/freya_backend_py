from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.database import engine, Base
from app.routers import auth_router, admin_router
from app.middleware.cors_proxy import CorsProxyMiddleware
from app.middleware.language import LanguageMiddleware

# Load environment variables
load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    # Create database tables
    Base.metadata.create_all(bind=engine)
    yield
    # Shutdown
    pass

app = FastAPI(
    title="Freya Salon Backend API",
    description="Backend API for Freya Beauty Salon management system",
    version="2.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS configuration
origins = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://freya-admin-frontend.vercel.app",
    "https://freya-admin-frontend-git-main-muhammadbekdev.vercel.app",
    "https://freya-admin-frontend-muhammadbekdev.vercel.app",
    "https://freya-salon-backend-cc373ce6622a.herokuapp.com",
    "https://freya-salon-backend.herokuapp.com"
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
        allowed_hosts=["freya-salon-backend-cc373ce6622a.herokuapp.com", "*.herokuapp.com"]
    )

# Include routers
app.include_router(auth_router, prefix="/api")
app.include_router(admin_router, prefix="/api")

# Static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

@app.get("/")
async def root():
    return {
        "message": "Freya Backend API is running",
        "environment": os.getenv("NODE_ENV", "development"),
        "port": os.getenv("PORT", "8000"),
        "database": "configured"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "freya-backend"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)