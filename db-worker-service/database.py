import os

from sqlalchemy import URL, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
POSTGRES_SERVER = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "tea_house")

SQLALCHEMY_DATABASE_URL = URL.create(
    drivername="postgresql+psycopg2",
    username=POSTGRES_USER,
    password=POSTGRES_PASSWORD,
    host=POSTGRES_SERVER,
    port=POSTGRES_PORT,
    database=POSTGRES_DB,
)

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()