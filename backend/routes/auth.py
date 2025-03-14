import os
import httpx
from dotenv import load_dotenv
from fastapi import HTTPException, status, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field
from pydantic_core import Url
from sqlalchemy.orm import Session
from helper.database import get_db
from models.user import User
from urllib.parse import urlencode
from google.auth.transport import requests
from google.oauth2 import id_token

router = APIRouter()
load_dotenv()
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
FRONTEND_URL = os.getenv("FRONTEND_URL")

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKEN_INFO_URL = "https://www.googleapis.com/oauth2/v3/tokeninfo"
SCOPES = "openid profile email"  # 'openid' is required for OIDC


class UserRequest(BaseModel):
	email: str
	name: str
	role: str = Field(default="user")


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user_request: UserRequest, db: Session = Depends(get_db)):
	new_user = User(**user_request.model_dump())
	db.add(new_user)
	db.commit()


@router.post("/login")
async def login():
	"""
	Redirects the user to Google's OAuth 2.0 authorization endpoint.
	The user is asked to authenticate and consent to the requested scopes.
	"""
	params = {
		"client_id": GOOGLE_CLIENT_ID,
		"redirect_uri": GOOGLE_REDIRECT_URI,
		"response_type": "code",  # Authorization Code Flow
		"scope": SCOPES,
		"access_type": "offline",  # Request refresh token (if needed)
		"prompt": "consent",  # Force consent screen for refresh token grant
		# In production, add a 'state' parameter for CSRF protection.
	}

	auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
	return JSONResponse({"url": auth_url})


@router.get("/callback")
async def google_auth_callback(
	response: Response,
	code: str = None,
	error: str = None,
	db: Session = Depends(get_db),
):
	"""Exchange the authorization code for an access token from Google"""
	if error:
		raise HTTPException(status_code=400, detail=f"Error during login: {error}")
	if not code:
		raise HTTPException(status_code=400, detail=f"No authorizatio code in callback")

	token_data = {
		"code": code,
		"client_id": GOOGLE_CLIENT_ID,
		"client_secret": GOOGLE_CLIENT_SECRET,
		"redirect_uri": GOOGLE_REDIRECT_URI,
		"grant_type": "authorization_code",
	}
	token_response = httpx.post(GOOGLE_TOKEN_URL, data=token_data)
	if token_response.status_code != 200:
		raise HTTPException(
			status_code=token_response.status_code,
			detail="Failed to obtain tokens from Google",
		)
	tokens = token_response.json()
	access_token = tokens.get("access_token")
	id_token_str = tokens.get("id_token")
	# refresh_token = tokens.get("refresh_token")

	if not id_token_str:
		raise HTTPException(
			status_code=400, detail="ID token not provided in token response"
		)
	if not access_token:
		raise HTTPException(
			status_code=400, detail="Access token not provided in token response"
		)
	# -----------------------------------------------------------------------------
	# Verify the ID token using Google's public keys.
	# This step ensures the token is genuine and was meant for our application.
	# -----------------------------------------------------------------------------
	try:
		request_adapter = requests.Request()
		decoded_id_token = id_token.verify_oauth2_token(
			id_token=id_token_str, request=request_adapter, audience=GOOGLE_CLIENT_ID
		)
	except Exception as e:
		raise HTTPException(
			status_code=401, detail=f"Failed to verify ID token: {str(e)}"
		)
	# -----------------------------------------------------------------------------
	# At this point the user is authenticated.
	# -----------------------------------------------------------------------------
	user_info = {
		"google_id": decoded_id_token.get("sub"),
		"email": decoded_id_token.get("email"),
		"name": decoded_id_token.get("name"),
		"picture": decoded_id_token.get("picture"),
	}
	# -----------------------------------------------------------------------------
	# If the user is not saved in out DB, add it
	# -----------------------------------------------------------------------------
	user = db.query(User).filter(User.google_id == user_info["google_id"]).first()
	if not user:
		new_user = User(
			google_id=user_info["google_id"],
			email=user_info["email"],
			name=user_info["name"],
			picture=user_info["picture"],
		)
		db.add(new_user)
		db.commit()
	# -----------------------------------------------------------------------------
	# Set access_token in cookie
	# -----------------------------------------------------------------------------
	# Create a RedirectResponse instead of using the response parameter
	redirect_response = RedirectResponse(f"{FRONTEND_URL}/dashboard")
	
	# Set the cookie on the redirect_response
	redirect_response.set_cookie(
		key="access_token",
		value=access_token,
		httponly=True,
		# Add these additional parameters for better security
		secure=False,  # Use only in HTTPS
		samesite="lax"  # Helps prevent CSRF
	)
	
	return redirect_response

@router.get("/test")
def test(request: Request, response: Response):
	response.set_cookie(
		key="test",
		value="blablablabla",
		httponly=True,
  		samesite="None"
	)

	return JSONResponse({"url": "Hello world"})
