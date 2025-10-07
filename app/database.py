from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from app.config import settings

# Create database engine (reads from settings.database_url)
db_url = settings.database_url

url = make_url(db_url)

# Connection args: adjust for SQLite
connect_args = {}
if url.get_backend_name() == "sqlite":
    connect_args = {"check_same_thread": False}

engine = create_engine(
    db_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    echo=False,
    connect_args=connect_args,
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class without Postgres schema (MySQL does not use schemas)
Base = declarative_base(metadata=MetaData())

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *

# No Postgres-specific schema handling needed

try:
    Base.metadata.create_all(engine)
except Exception as e:
    # Delay hard failure to runtime endpoints; helps server boot for config/debug
    print(f"[DB INIT] Table creation skipped due to error: {e}")

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()