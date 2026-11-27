import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import (
    COOKIE_NAME,
    SESSION_DURATION,
    verify_credentials,
    create_admin_session,
    revoke_admin_session,
    require_admin,
    enforce_login_rate_limit,
    verify_auth_origin,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@router.post(
    "/login",
    dependencies=[
        Depends(verify_auth_origin),
        Depends(enforce_login_rate_limit),
    ],
)

def login(
    credentials: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    if not verify_credentials(
        credentials.username,
        credentials.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password",
        )

    token = create_admin_session(db)

    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=os.getenv("APP_ENV") != "development",
        samesite="strict",
        path="/",
    )

    response.headers["Cache-Control"] = "no-store"

    return {"status": "authenticated"}


@router.post(
    "/logout",
    dependencies=[Depends(verify_auth_origin)],
)

def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    token = request.cookies.get(COOKIE_NAME)

    if token:
        revoke_admin_session(db, token)

    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=os.getenv("APP_ENV") != "development",
        samesite="strict",
    )

    response.headers["Cache-Control"] = "no-store"

    return {"status": "logged_out"}


@router.get("/me")
def check_session(
    response: Response,
    session=Depends(require_admin),
):
    response.headers["Cache-Control"] = "no-store"

    return {"authenticated": True}