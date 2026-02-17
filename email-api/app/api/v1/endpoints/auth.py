"""Authentication endpoints."""
import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.core.config import get_settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.db.repositories.user import get_user_by_email, create_user
from app.models.user import Token, UserCreate, UserResponse
from app.services.token_manager import save_google_tokens

router = APIRouter()

# Health check so we can confirm auth routes are loaded (GET /api/v1/auth/ok)
@router.get("/ok")
async def auth_ok():
    """Confirm auth router is loaded. Returns 200 if Google login is configured."""
    settings = get_settings()
    return {"status": "ok", "google_configured": bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)}

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# Gmail API + profile scopes (no app password needed)
GOOGLE_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]


@router.get("/google")
async def google_login():
    """Redirect to Google consent screen. Requests Gmail + profile scopes for email sync without app password."""
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
    base = settings.BACKEND_URL.rstrip("/")
    redirect_uri = f"{base}{settings.API_V1_PREFIX}/auth/google/callback"
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "access_type": "offline",
        "prompt": "consent",  # Force refresh_token every time for first-time users
    }
    url = f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=url)


@router.get("/google/callback")
async def google_callback(code: str | None = None, error: str | None = None, db: AsyncSession = Depends(get_db)):
    """Exchange Google code for user info, create/find user, redirect to frontend with JWT."""
    settings = get_settings()
    if error:
        frontend = settings.FRONTEND_URL.rstrip("/")
        return RedirectResponse(url=f"{frontend}/login?error=access_denied")
    if not code:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_code")
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=not_configured")

    base = settings.BACKEND_URL.rstrip("/")
    redirect_uri = f"{base}{settings.API_V1_PREFIX}/auth/google/callback"
    async with httpx.AsyncClient() as client:
        token_res = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    if token_res.status_code != 200:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=token_exchange_failed")

    data = token_res.json()
    access_token = data.get("access_token")
    refresh_token = data.get("refresh_token")
    expires_in = data.get("expires_in")
    if not access_token:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_token")

    async with httpx.AsyncClient() as client:
        user_res = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if user_res.status_code != 200:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=userinfo_failed")

    user_info = user_res.json()
    email = user_info.get("email")
    name = user_info.get("name") or (email.split("@")[0] if email else "User")
    if not email:
        return RedirectResponse(url=f"{settings.FRONTEND_URL.rstrip('/')}/login?error=no_email")

    import secrets
    user = await get_user_by_email(db, email)
    if not user:
        user = await create_user(
            db,
            email=email,
            password=secrets.token_urlsafe(32),
            full_name=name,
            role="faculty",
        )
    await save_google_tokens(db, user.id, access_token, refresh_token, expires_in)
    await db.commit()

    jwt_token = create_access_token(subject=user.email)
    frontend = settings.FRONTEND_URL.rstrip("/")
    return RedirectResponse(url=f"{frontend}/login?token={jwt_token}")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """Login with email (username) and password; return JWT access token."""
    email = form_data.username  # OAuth2 form uses "username" for email
    user = await get_user_by_email(db, email)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User inactive")
    access_token = create_access_token(subject=user.email)
    return Token(access_token=access_token, token_type="bearer")


@router.post("/register", response_model=UserResponse)
async def register(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user (e.g. faculty)."""
    from app.db.repositories.user import create_user
    existing = await get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    user = await create_user(
        db,
        email=user_in.email,
        password=user_in.password,
        full_name=user_in.full_name,
        role=user_in.role,
    )
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
    )
