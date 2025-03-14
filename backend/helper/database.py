from sqlalchemy.orm import Session
from config.database import session_maker

def get_db():
	try:
		db: Session = session_maker()
		yield db
	finally:
		db.close()