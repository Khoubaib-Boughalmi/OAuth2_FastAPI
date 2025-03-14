from sqlalchemy import Column, Integer, String
from config.database import Base

class User(Base):
	__tablename__ = "Users"
	
	id: int = Column(Integer, primary_key=True, index=True)
	google_id: int = Column(String, unique=True, index=True, nullable=False)
	email: str = Column(String, unique=True, nullable=False)
	name: str = Column(String)
	role: str = Column(String, default="user")
	picture: str = Column(String)