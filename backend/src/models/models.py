import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, Boolean, Enum, Text, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from datetime import datetime
import enum
import uuid


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    groups = relationship("Group", secondary="group_members", back_populates="members")
    expenses_paid = relationship("Expense", back_populates="paid_by_user")


class Group(Base):
    __tablename__ = "groups"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    # Relationships
    members = relationship("User", secondary="group_members", back_populates="groups")
    expenses = relationship("Expense", back_populates="group")
    group_members = relationship("GroupMember", back_populates="group")


class GroupMember(Base):
    __tablename__ = "group_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    left_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    group = relationship("Group", back_populates="group_members")
    user = relationship("User")


class SplitType(str, enum.Enum):
    EQUAL = "equal"
    UNEQUAL = "unequal"
    PERCENTAGE = "percentage"
    SHARE = "share"


class Currency(str, enum.Enum):
    INR = "INR"
    USD = "USD"
    EUR = "EUR"


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=False)
    description = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    paid_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    split_type = Column(String(20), nullable=False)
    expense_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(Text)
    is_deleted = Column(Boolean, default=False)
    is_settlement = Column(Boolean, default=False)
    csv_row_number = Column(Integer, nullable=True)  # Track original CSV row

    # Relationships
    group = relationship("Group", back_populates="expenses")
    paid_by_user = relationship("User", back_populates="expenses_paid")
    splits = relationship("ExpenseSplit", back_populates="expense", cascade="all, delete-orphan")


class ExpenseSplit(Base):
    __tablename__ = "expense_splits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    expense_id = Column(String(36), ForeignKey("expenses.id"), nullable=False)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    percentage = Column(Float, nullable=True)
    shares = Column(Integer, nullable=True)

    # Relationships
    expense = relationship("Expense", back_populates="splits")
    user = relationship("User")


class ImportReport(Base):
    __tablename__ = "import_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    group_id = Column(String(36), ForeignKey("groups.id"), nullable=False)
    import_date = Column(DateTime, default=datetime.utcnow)
    total_rows = Column(Integer, nullable=False)
    successful_imports = Column(Integer, nullable=False)
    anomalies_detected = Column(JSON, nullable=False)
    created_by = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Relationships
    group = relationship("Group")
    created_by_user = relationship("User")
