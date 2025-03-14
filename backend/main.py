from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes import auth
from models import user
from config.database import engine


app = FastAPI()

user.Base.metadata.create_all(bind=engine)

origins = ["http://localhost:5173"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,  # Allow credentials (cookies)
    allow_methods=["*"],  # Allow all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
app.include_router(auth.router)