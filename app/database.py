from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from app.config import settings

# Create database engine (reads from settings.database_url)
db_url = settings.database_url

# Normalize legacy postgres scheme to postgresql for SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

url = make_url(db_url)

# Apply Postgres-specific connect args only when using Postgres
connect_args = {}
if url.get_backend_name() == "postgresql":
    connect_args = {"options": "-c search_path=public"}

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    connect_args=connect_args,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class with default schema set to public
Base = declarative_base(metadata=MetaData(schema="public"))

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *

# Ensure 'public' schema exists for Postgres before creating tables
if url.get_backend_name() == "postgresql":
    # Use a transaction that commits automatically
    with engine.begin() as conn:
        conn.execute(text("CREATE SCHEMA IF NOT EXISTS public"))

Base.metadata.create_all(engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()