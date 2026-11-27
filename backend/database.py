import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()    #Loading the values from the .env file

DATABASE_URL = os.environ["DATABASE_URL"]

# create_engine creates the central mechanism through which Python communicates with PostgreSQL
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping= True,
)

# sessionmaker - Creates a factory that produces database sessions whenever we need them
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)

# DeclarativeBase - Helps us define database tables using Python class
class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()