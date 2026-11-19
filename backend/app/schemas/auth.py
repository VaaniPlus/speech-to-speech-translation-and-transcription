"""Authentication request and response schemas."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

EmailText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=254),
]
PasswordText = Annotated[str, StringConstraints(min_length=8, max_length=128)]


class AuthRequest(BaseModel):
    """Credentials submitted for registration or login."""

    model_config = ConfigDict(extra="forbid")

    email: EmailText
    password: PasswordText

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        normalized = value.lower()
        if normalized.count("@") != 1 or normalized.startswith("@") or normalized.endswith("@"):
            raise ValueError("email must be valid")
        return normalized


class UserResponse(BaseModel):
    """Public user information."""

    id: int
    email: str


class TokenResponse(BaseModel):
    """Bearer access token returned after successful authentication."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse
