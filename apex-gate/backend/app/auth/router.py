from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.limiter import limiter

from app.auth.database import get_auth_session
from app.auth.deps import get_current_user
from app.auth.models import RefreshToken, User
from app.auth.schemas import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserResponse, UserUpdate
from app.auth.service import (
    create_access_token,
    create_refresh_token,
    hash_password,
    rotate_refresh_token,
    store_refresh_token,
    verify_password,
)
from app.crypto import sha256_hash

router = APIRouter(prefix="/auth", tags=["auth"])


async def _is_first_user(db: AsyncSession) -> bool:
    result = await db.execute(select(func.count()).select_from(User))
    return result.scalar_one() == 0


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def register(request: Request, body: RegisterRequest, db: AsyncSession = Depends(get_auth_session)) -> User:
    first_user = await _is_first_user(db)

    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username or email already registered")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_admin=first_user,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_auth_session)) -> TokenResponse:
    result = await db.execute(select(User).where(User.username == body.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    refresh_token = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh_token, db)
    return TokenResponse(access_token=create_access_token(user.id), refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_auth_session)) -> TokenResponse:
    access_token, new_refresh = await rotate_refresh_token(body.refresh_token, db)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(body: RefreshRequest, db: AsyncSession = Depends(get_auth_session)) -> dict:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == sha256_hash(body.refresh_token)))
    record = result.scalar_one_or_none()
    if record:
        record.revoked = True
        await db.commit()
    return {"message": "Logged out"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_auth_session),
) -> User:
    if body.new_password is not None:
        if body.current_password is None or not verify_password(body.current_password, current_user.hashed_password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")
        current_user.hashed_password = hash_password(body.new_password)

    if body.username is not None:
        existing = await db.scalar(
            select(User).where(User.username == body.username, User.id != current_user.id)
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
        current_user.username = body.username
    if body.email is not None:
        existing = await db.scalar(
            select(User).where(User.email == body.email, User.id != current_user.id)
        )
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already taken")
        current_user.email = body.email

    await db.commit()
    await db.refresh(current_user)
    return current_user
