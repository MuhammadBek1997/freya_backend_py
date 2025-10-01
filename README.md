# Freya Salon Backend - Python/FastAPI

Backend API for Freya Beauty Salon management system built with Python and FastAPI.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **SQLAlchemy ORM**: Database operations with PostgreSQL
- **JWT Authentication**: Secure authentication system
- **Swagger Documentation**: Auto-generated API documentation
- **Multi-language Support**: Internationalization (i18n)
- **External Integrations**:
  - Eskiz.uz SMS service
  - Click payment system
  - DeepL translation service
- **Real-time Communication**: WebSocket support
- **File Upload**: Image and file handling

## Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment variables:
   ```bash
   cp .env.example .env
   ```
4. Update `.env` file with your configuration
5. Run the application:
   ```bash
   uvicorn main:app --reload
   ```

## API Documentation

- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

## Environment Variables

See `.env.example` for required environment variables.

## Deployment

This application is configured for deployment on Heroku with the included `Procfile` and `runtime.txt`.

## Project Structure

```
freya_backend_python/
├── app/
│   ├── models/          # Database models
│   ├── schemas/         # Pydantic schemas
│   ├── routers/         # API routes
│   ├── services/        # Business logic
│   ├── middleware/      # Custom middleware
│   ├── utils/           # Utility functions
│   ├── config.py        # Configuration
│   └── database.py      # Database setup
├── main.py              # Application entry point
├── requirements.txt     # Python dependencies
└── .env.example         # Environment variables template
```