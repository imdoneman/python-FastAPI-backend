# Handles connections and sessions
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Uses PostgreSQL URL if available (Prod/Docker), otherwise falls back to local SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tea_house.db")

# SQLite requires an extra argument to allow safe cross-thread handling
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith(
    "sqlite") else {}

# 1. Initialize the engine connection
engine = create_engine(DATABASE_URL, connect_args=connect_args)

# 2. Create an isolated database session engine
session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 3. Define the base class that maps our Python classes to SQL tables
Base = declarative_base()

# 4. Dependency Injection function to open/close DB sessions per API request


def get_db():
    db = session_local()
    try:
        yield db
    finally:
        db.close()
