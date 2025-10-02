from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,
    # Ensure default schema is set to public to avoid InvalidSchemaName errors
    connect_args={"options": "-c search_path=public"}
    # echo=settings.environment == "development"
)

# Create SessionLocal class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create Base class with default schema set to public
Base = declarative_base(metadata=MetaData(schema="public"))

# Import all models to ensure they are registered with SQLAlchemy
from app.models import *
Base.metadata.create_all(engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()