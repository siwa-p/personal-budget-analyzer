from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    theme: Optional[str] = "light"

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: Optional[str] = None
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = Field(default=None, min_length=8)
    theme: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserRead(UserBase):
    id: int
    is_active: bool
    is_superuser: bool
    theme: str
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class Message(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)
