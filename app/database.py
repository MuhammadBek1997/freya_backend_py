from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from app.config import settings

# Create database engine
engine = create_engine(
    "postgresql://u82hhsnrq03vdb:p894645a6da7b84f388ce131c8306b8bf2c5c3a5c7b32d2e5cd60987b1c644d1f@c3mvmsjsgbq96j.cluster-czz5s0kz4scl.eu-west-1.rds.amazonaws.com:5432/d7cho3buhj3j6g",
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