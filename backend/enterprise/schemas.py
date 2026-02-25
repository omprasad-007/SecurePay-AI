from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from .models import TransactionStatus, TransactionType, UserRole


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class AuthLoginRequest(BaseModel):
    google_id_token: str | None = None
    email: EmailStr | None = None
    full_name: str | None = None
    organization_name: str | None = None
    invite_token: str | None = None


class AuthRefreshRequest(BaseModel):
    refresh_token: str


class OrganizationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    fraud_threshold: float
    created_at: datetime


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    email: EmailStr
    full_name: str | None
    role: UserRole
    two_factor_enabled: bool
    is_active: bool
    created_at: datetime


class AuthLoginResponse(BaseModel):
    tokens: TokenPair
    user: UserOut
    organization: OrganizationOut


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    slug: str = Field(min_length=2, max_length=180)
    fraud_threshold: float = Field(default=70.0, ge=0, le=100)


class FraudThresholdUpdate(BaseModel):
    fraud_threshold: float = Field(ge=0, le=100)


class InviteUserRequest(BaseModel):
    email: EmailStr
    role: UserRole

    @field_validator("role")
    @classmethod
    def valid_invite_role(cls, value: UserRole) -> UserRole:
        if value == UserRole.SUPER_ADMIN:
            raise ValueError("Cannot invite SUPER_ADMIN")
        return value


class InviteUserResponse(BaseModel):
    invite_id: str
    email: EmailStr
    role: UserRole
    organization_id: str
    invite_token: str
    expires_at: datetime


class TransactionBase(BaseModel):
    upi_id: str = Field(min_length=3, max_length=180)
    sender_name: str | None = Field(default=None, max_length=180)
    receiver_name: str | None = Field(default=None, max_length=180)
    merchant_name: str = Field(min_length=2, max_length=180)
    merchant_category: str | None = Field(default=None, max_length=180)

    transaction_amount: float = Field(gt=0)
    currency: str = Field(default="INR", min_length=3, max_length=10)
    transaction_type: TransactionType
    transaction_status: TransactionStatus

    transaction_date: date
    transaction_time: time

    geo_latitude: float | None = Field(default=None, ge=-90, le=90)
    geo_longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)

    ip_address: str | None = Field(default=None, max_length=64)
    device_id: str | None = Field(default=None, max_length=180)
    device_type: str | None = Field(default=None, max_length=100)

    notes: str | None = None
    tags: list[str] = Field(default_factory=list)


class TransactionCreate(TransactionBase):
    user_id: str | None = None


class TransactionUpdate(BaseModel):
    upi_id: str | None = Field(default=None, min_length=3, max_length=180)
    sender_name: str | None = Field(default=None, max_length=180)
    receiver_name: str | None = Field(default=None, max_length=180)
    merchant_name: str | None = Field(default=None, min_length=2, max_length=180)
    merchant_category: str | None = Field(default=None, max_length=180)

    transaction_amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=10)
    transaction_type: TransactionType | None = None
    transaction_status: TransactionStatus | None = None

    transaction_date: date | None = None
    transaction_time: time | None = None

    geo_latitude: float | None = Field(default=None, ge=-90, le=90)
    geo_longitude: float | None = Field(default=None, ge=-180, le=180)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    country: str | None = Field(default=None, max_length=100)

    ip_address: str | None = Field(default=None, max_length=64)
    device_id: str | None = Field(default=None, max_length=180)
    device_type: str | None = Field(default=None, max_length=100)

    notes: str | None = None
    tags: list[str] | None = None
    is_frozen: bool | None = None


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    transaction_id: str = Field(alias="id")
    upi_id: str
    sender_name: str | None
    receiver_name: str | None
    merchant_name: str
    merchant_category: str | None
    transaction_amount: float
    currency: str
    transaction_type: TransactionType
    transaction_status: TransactionStatus

    transaction_date: date
    transaction_time: time

    geo_latitude: float | None
    geo_longitude: float | None
    city: str | None
    state: str | None
    country: str | None

    ip_address: str | None
    device_id: str | None
    device_type: str | None

    risk_score: float
    is_flagged: bool
    is_frozen: bool
    notes: str | None
    tags: list[str]
    fraud_signals: list[str]

    user_id: str
    created_by: str
    organization_id: str
    created_at: datetime
    updated_at: datetime


class TransactionListResponse(BaseModel):
    items: list[TransactionOut]
    total: int
    page: int
    page_size: int


class TransactionExportRequest(BaseModel):
    format: str = Field(default="csv")
    fraud_only: bool = False


class TransactionCommentCreate(BaseModel):
    comment: str = Field(min_length=1, max_length=2000)


class TransactionCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    transaction_id: str
    user_id: str
    comment: str
    created_at: datetime


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: str = Field(alias="id")
    user_id: str
    organization_id: str | None
    action_type: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    ip_address: str | None
    details: dict[str, Any]


class AuditListResponse(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
