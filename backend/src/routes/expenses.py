import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Dict, Any, Optional
from database import get_db
from schemas import ExpenseCreate, ExpenseResponse, ImportReportResponse, AnomalyReport
from middleware.auth import get_current_user
from models.models import Expense, ExpenseSplit, ImportReport, Group, User, GroupMember
from services.csv_importer import CSVImporter
from services.expense_service import ExpenseService
import json
import uuid
from datetime import datetime
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["expenses", "import"])


# ===== BULK IMPORT SCHEMAS =====
class ImportedExpense(BaseModel):
    description: str
    amount: float
    currency: str
    paid_by: str
    split_type: str
    expense_date: datetime
    split_with: List[str]
    split_details: Dict[str, float] = {}
    notes: Optional[str] = None
    is_settlement: bool = False
    csv_row_number: Optional[int] = None


class BulkImportRequest(BaseModel):
    expenses: List[ImportedExpense]
    anomalies: List[Dict[str, Any]] = []


class SettlementRequest(BaseModel):
    from_user_id: str
    to_user_id: str
    amount: float
    currency: str = "INR"
    expense_date: datetime
    notes: Optional[str] = None


# Helper function to find or create group members by name during CSV import
def get_or_create_member_by_name(group_id: str, name: str, db: Session) -> User:
    norm_name = name.strip()
    
    # Check if a user with this full name or username already exists
    user = db.query(User).filter(
        or_(
            User.full_name == norm_name,
            User.username == norm_name.lower()
        )
    ).first()
    
    if not user:
        # Create a new placeholder/guest user
        username = norm_name.lower().replace(" ", "_")
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            username = f"{username}_{uuid.uuid4().hex[:4]}"
            
        user = User(
            id=str(uuid.uuid4()),
            username=username,
            email=f"{username}@example.com",
            full_name=norm_name,
            hashed_password=""  # Empty password for guest accounts
        )
        db.add(user)
        db.flush()
        
    # Check if user is already a member of the group
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user.id
    ).first()
    
    if not member:
        # Add guest user to the group
        member = GroupMember(
            id=str(uuid.uuid4()),
            group_id=group_id,
            user_id=user.id,
            joined_at=datetime(2026, 2, 1)  # Default join date corresponding to start of logs
        )
        db.add(member)
        db.flush()
        
    return user


@router.post("/{group_id}/expenses", response_model=ExpenseResponse)
async def create_expense(
    group_id: str,
    expense_data: ExpenseCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new manual expense"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    expense = Expense(
        id=str(uuid.uuid4()),
        group_id=group_id,
        description=expense_data.description,
        amount=expense_data.amount,
        currency=expense_data.currency,
        paid_by_user_id=expense_data.paid_by_user_id,
        split_type=expense_data.split_type,
        expense_date=expense_data.expense_date,
        notes=expense_data.notes,
        is_settlement=False
    )
    
    db.add(expense)
    db.flush()
    
    for split_detail in expense_data.split_details:
        split = ExpenseSplit(
            id=str(uuid.uuid4()),
            expense_id=expense.id,
            user_id=split_detail.user_id,
            amount=split_detail.amount or 0.0,
            percentage=split_detail.percentage,
            shares=split_detail.shares
        )
        db.add(split)
    
    db.commit()
    db.refresh(expense)
    
    return ExpenseResponse.model_validate(expense)


@router.post("/groups/{group_id}/parse-csv")
async def parse_expenses_csv(
    group_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Parse CSV and extract expenses and anomalies for interactive preview"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    content = await file.read()
    csv_content = content.decode("utf-8")
    
    # Retrieve current group member active timelines
    members = db.query(GroupMember).filter(GroupMember.group_id == group_id).all()
    member_timelines = {}
    
    importer = CSVImporter()
    for m in members:
        user = m.user
        norm_key = importer._normalize_name(user.full_name or user.username)
        member_timelines[norm_key] = (m.joined_at, m.left_at)
        norm_uname = importer._normalize_name(user.username)
        member_timelines[norm_uname] = (m.joined_at, m.left_at)
    
    parsed_expenses, anomalies = importer.parse_csv(csv_content, member_timelines)
    
    # Format datetimes for JSON response
    for exp in parsed_expenses:
        exp["expense_date"] = exp["expense_date"].isoformat()
        
    return {
        "total_rows": importer.processed_rows,
        "successful_imports": len(parsed_expenses),
        "anomalies": [a.to_dict() for a in anomalies],
        "parsed_expenses": parsed_expenses
    }


@router.post("/groups/{group_id}/import-csv")
async def import_approved_expenses(
    group_id: str,
    import_data: BulkImportRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import approved expenses from the interactive review screen"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Save the import report first
    import_report = ImportReport(
        id=str(uuid.uuid4()),
        group_id=group_id,
        total_rows=len(import_data.expenses),
        successful_imports=len(import_data.expenses),
        anomalies_detected=json.dumps(import_data.anomalies),
        created_by=current_user.id
    )
    db.add(import_report)
    db.flush()
    
    for exp_data in import_data.expenses:
        # Resolve or auto-create payer
        payer = get_or_create_member_by_name(group_id, exp_data.paid_by, db)
        
        expense = Expense(
            id=str(uuid.uuid4()),
            group_id=group_id,
            description=exp_data.description,
            amount=exp_data.amount,
            currency=exp_data.currency,
            paid_by_user_id=payer.id,
            split_type=exp_data.split_type,
            expense_date=exp_data.expense_date,
            notes=exp_data.notes,
            is_settlement=exp_data.is_settlement,
            csv_row_number=exp_data.csv_row_number
        )
        db.add(expense)
        db.flush()
        
        # Add splits
        for participant_name in exp_data.split_with:
            split_user = get_or_create_member_by_name(group_id, participant_name, db)
            
            # Extract details
            amount = exp_data.split_details.get(participant_name, 0.0) if exp_data.split_type == "unequal" else 0.0
            percentage = exp_data.split_details.get(participant_name, 0.0) if exp_data.split_type == "percentage" else None
            shares = int(exp_data.split_details.get(participant_name, 1)) if exp_data.split_type == "share" else None
            
            split = ExpenseSplit(
                id=str(uuid.uuid4()),
                expense_id=expense.id,
                user_id=split_user.id,
                amount=amount,
                percentage=percentage,
                shares=shares
            )
            db.add(split)
            
    db.commit()
    return {
        "report_id": import_report.id,
        "message": f"Successfully imported {len(import_data.expenses)} entries."
    }


@router.post("/groups/{group_id}/settlements")
async def record_settlement(
    group_id: str,
    settlement_data: SettlementRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Record a settlement payment between group members"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        
    sender = db.query(User).filter(User.id == settlement_data.from_user_id).first()
    recipient = db.query(User).filter(User.id == settlement_data.to_user_id).first()
    if not sender or not recipient:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sender or recipient not found")
        
    # Create settlement as an Expense with is_settlement = True
    expense = Expense(
        id=str(uuid.uuid4()),
        group_id=group_id,
        description=f"Settlement: {sender.full_name or sender.username} paid {recipient.full_name or recipient.username}",
        amount=settlement_data.amount,
        currency=settlement_data.currency,
        paid_by_user_id=settlement_data.from_user_id,
        split_type="equal",
        expense_date=settlement_data.expense_date,
        is_settlement=True,
        notes=settlement_data.notes
    )
    db.add(expense)
    db.flush()
    
    # Split represents the recipient
    split = ExpenseSplit(
        id=str(uuid.uuid4()),
        expense_id=expense.id,
        user_id=settlement_data.to_user_id,
        amount=settlement_data.amount
    )
    db.add(split)
    db.commit()
    
    return {"message": "Settlement recorded successfully"}


@router.get("/groups/{group_id}/import-report/{report_id}", response_model=ImportReportResponse)
async def get_import_report(
    group_id: str,
    report_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details of a past CSV import report"""
    report = db.query(ImportReport).filter(ImportReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    
    anomalies_data = json.loads(report.anomalies_detected)
    anomalies = [AnomalyReport(**a) for a in anomalies_data]
    
    return {
        "id": report.id,
        "total_rows": report.total_rows,
        "successful_imports": report.successful_imports,
        "anomalies": anomalies,
        "created_at": report.import_date
    }


@router.get("/groups/{group_id}/expenses")
async def get_group_expenses(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all non-deleted expenses for a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    expenses = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False
    ).order_by(Expense.expense_date.desc()).all()
    
    return [ExpenseResponse.model_validate(e) for e in expenses]


@router.get("/groups/{group_id}/members/{user_id}/breakdown")
async def get_member_breakdown(
    group_id: str,
    user_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a detailed expense-by-expense breakdown for a group member"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        
    breakdown = ExpenseService.get_user_expense_breakdown(group_id, user_id, db)
    return breakdown


@router.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete an expense"""
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    
    expense.is_deleted = True
    db.commit()
    
    return {"message": "Expense deleted"}
