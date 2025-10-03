from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import make_url
from app.config import settings

# Create database engine (reads from settings.database_url)
db_url = settings.database_url

url = make_url(db_url)

# Connection args: keep minimal for MySQL; none needed for mysqlconnector
connect_args = {}

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

Base.metadata.create_all(engine)

# Dependency to get database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()