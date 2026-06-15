from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ===== AUTH SCHEMAS =====
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# ===== GROUP SCHEMAS =====
class GroupMemberResponse(BaseModel):
    id: str
    user_id: str
    joined_at: datetime
    left_at: Optional[datetime] = None
    is_active: bool

    class Config:
        from_attributes = True


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    member_emails: Optional[List[str]] = []


class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    created_by: str
    created_at: datetime
    is_active: bool
    members: List[UserResponse] = []

    class Config:
        from_attributes = True


# ===== EXPENSE SCHEMAS =====
class SplitDetail(BaseModel):
    user_id: str
    amount: Optional[float] = None
    percentage: Optional[float] = None
    shares: Optional[int] = None


class ExpenseCreate(BaseModel):
    description: str
    amount: float = Field(..., gt=0)
    currency: str = "INR"
    paid_by_user_id: str
    split_type: str
    expense_date: datetime
    split_details: List[SplitDetail]
    notes: Optional[str] = None


class ExpenseResponse(BaseModel):
    id: str
    description: str
    amount: float
    currency: str
    paid_by_user_id: str
    split_type: str
    expense_date: datetime
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SettlementCreate(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: float = Field(..., gt=0)
    currency: str = "INR"


# ===== IMPORT SCHEMAS =====
class AnomalyReport(BaseModel):
    row_number: Optional[int]
    field: str
    issue: str
    original_value: Any
    action_taken: str
    severity: str  # "error", "warning", "info"


class ImportReportResponse(BaseModel):
    id: str
    total_rows: int
    successful_imports: int
    anomalies: List[AnomalyReport]
    created_at: datetime

    class Config:
        from_attributes = True


# ===== BALANCE SCHEMAS =====
class BalanceDetail(BaseModel):
    expense_id: str
    description: str
    amount: float
    currency: str
    paid_by: str
    your_share: float
    date: datetime


class UserBalance(BaseModel):
    user_id: str
    user_name: str
    amount: float  # Positive: user owes, Negative: user is owed
    currency: str


class GroupBalance(BaseModel):
    user_id: str
    user_name: str
    owes_amount: float
    owed_by_amount: float
    net_balance: float  # Positive: owes, Negative: is owed


class SettlementSummary(BaseModel):
    from_user: str
    to_user: str
    amount: float
    currency: str
