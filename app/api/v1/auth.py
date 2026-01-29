from datetime import timedelta
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from jose import jwt, JWTError

from app.db.session import get_session
from app.models.user import User, UserCreate, UserRead, Token, TokenData, UserRole
from app.core import security
from app.core.config import settings
from fastapi.security import OAuth2PasswordBearer

router = APIRouter()
reusable_oauth2 = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def get_current_user(session: Session = Depends(get_session), token: str = Depends(reusable_oauth2)) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[security.ALGORITHM])
        token_data = TokenData(email=payload.get("sub"))
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Could not validate credentials",
        )
    user = session.exec(select(User).where(User.email == token_data.email)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

def check_role(roles: list[UserRole]):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user
    return role_checker

@router.post("/register", response_model=UserRead)
def register(user_in: UserCreate, session: Session = Depends(get_session)) -> Any:
    user = session.exec(select(User).where(User.email == user_in.email)).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    db_user = User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=user_in.role,
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.post("/login", response_model=Token)
def login(session: Session = Depends(get_session), form_data: OAuth2PasswordRequestForm = Depends()) -> Any:
    user = session.exec(select(User).where(User.email == form_data.username)).first()
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return {
        "access_token": security.create_access_token(user.email, expires_delta=access_token_expires),
        "token_type": "bearer",
    }

@router.get("/me", response_model=UserRead)
def read_user_me(current_user: User = Depends(get_current_user)) -> Any:
    return current_user

# @router.get("/users", response_model=list[UserRead])
# def list_users(role: UserRole = None, session: Session = Depends(get_session)) -> Any:
#     query = select(User)
#     if role:
#         query = query.where(User.role == role)
#     users = session.exec(query).all()
#     return users

@router.get("/users", response_model=List[UserRead])
def read_users(
    session: Session = Depends(get_session),
    role: Optional[UserRole] = None,
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get all users, optionally filtered by role.
    """
    query = select(User)
    if role:
        query = query.where(User.role == role)
    return session.exec(query).all()
