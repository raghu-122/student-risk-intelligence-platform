from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.database import get_db
from app.core.security import verify_password, create_access_token, hash_password
from app.models.user import User
from app.api.dependencies.auth import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    role: str
    username: str
    user_id: str


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate and return JWT access token."""
    user = db.query(User).filter(User.username == request.username, User.is_active == True).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.username, "role": user.role, "user_id": user.user_id})
    return TokenResponse(
        access_token=token, token_type="bearer",
        role=user.role, username=user.username, user_id=user.user_id,
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Return information about the authenticated user."""
    return {
        "user_id": current_user.user_id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
    }

