"""
CORS middleware for FastAPI
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_cors(app: FastAPI):
    """Setup CORS middleware"""
    
    # Allowed origins
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://localhost:5179",
        "http://localhost:5180",
        "http://localhost:5181",
        "http://localhost:5182",
        "http://localhost:5183",
        "http://localhost:4173",
        "https://freyabackend-parfa7zy7-muhammads-projects-3a6ae627.vercel.app",
        "https://freya-web-frontend.vercel.app",
        "https://freya-frontend.onrender.com",
        "https://freyasalon-6f0b3dc79e01.herokuapp.com",
        "https://freyajs.vercel.app",
        "https://freya-admin.vercel.app",
        "https://freya-admin.onrender.com",
        "https://freyajs-git-main-muhammads-projects-3a6ae627.vercel.app",
        "https://freyajs-muhammads-projects-3a6ae627.vercel.app"
    ]
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins for now
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=[
            "Origin",
            "X-Requested-With", 
            "Content-Type",
            "Accept",
            "Authorization",
            "X-Language",
            "X-User-language",
            "X-User-Language",
            "Accept-Language"
        ],
        expose_headers=["Content-Length", "X-Foo", "X-Bar"],
        max_age=86400  # 24 hours
    )
