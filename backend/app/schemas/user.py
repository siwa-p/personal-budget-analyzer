
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    theme: str | None = "light"

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    is_active: bool = True
    is_superuser: bool = False


class UserUpdate(BaseModel):
    username: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None
    password: str | None = Field(default=None, min_length=8)
    theme: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


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
    sub: str | None = None
    exp: int | None = None


class Message(BaseModel):
    message: str


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str = Field(..., min_length=10)
    new_password: str = Field(..., min_length=8)
