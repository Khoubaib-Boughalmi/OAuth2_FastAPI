from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

DATABASE_URL = "sqlite:///./database.sqlite3"

# create engine
engine = create_engine(url=DATABASE_URL, connect_args={"check_same_thread": False})

# create the enstantiable db session
session_maker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()