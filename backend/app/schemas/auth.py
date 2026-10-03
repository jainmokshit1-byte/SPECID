"""Request and response models for auth and users (API-01, API-02; DEC-14). Never a hash."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    role: str
    must_change_password: bool


class Me(BaseModel):
    id: uuid.UUID
    username: str
    display_name: str | None
    role: str
    cpse_id: uuid.UUID | None
    cpse_code: str | None
    must_change_password: bool


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=200)
    new_password: str = Field(min_length=1, max_length=200)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    display_name: str | None
    role: str
    cpse_id: uuid.UUID | None
    cpse_code: str | None = None
    is_active: bool
    must_change_password: bool
    last_login_at: datetime | None
    created_at: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    display_name: str | None = Field(default=None, max_length=200)
    role: str
    cpse_id: uuid.UUID | None = None
    temporary_password: str = Field(min_length=1, max_length=200)


class PasswordReset(BaseModel):
    temporary_password: str = Field(min_length=1, max_length=200)


class CpseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
