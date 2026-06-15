import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas import ExpenseCreate, ExpenseResponse, ImportReportResponse, AnomalyReport
from middleware.auth import get_current_user
from models.models import Expense, ExpenseSplit, ImportReport, Group
from services.csv_importer import CSVImporter
from services.expense_service import ExpenseService
import json
import uuid
from datetime import datetime

router = APIRouter(prefix="/api", tags=["expenses", "import"])


@router.post("/{group_id}/expenses", response_model=ExpenseResponse)
async def create_expense(
    group_id: str,
    expense_data: ExpenseCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new expense"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Create expense
    expense = Expense(
        id=str(uuid.uuid4()),
        group_id=group_id,
        description=expense_data.description,
        amount=expense_data.amount,
        currency=expense_data.currency,
        paid_by_user_id=expense_data.paid_by_user_id,
        split_type=expense_data.split_type,
        expense_date=expense_data.expense_date,
        notes=expense_data.notes
    )
    
    db.add(expense)
    db.flush()
    
    # Create splits
    for split_detail in expense_data.split_details:
        split = ExpenseSplit(
            id=str(uuid.uuid4()),
            expense_id=expense.id,
            user_id=split_detail.user_id,
            amount=split_detail.amount or 0,
            percentage=split_detail.percentage,
            shares=split_detail.shares
        )
        db.add(split)
    
    db.commit()
    db.refresh(expense)
    
    return ExpenseResponse.model_validate(expense)


@router.post("/groups/{group_id}/import-csv")
async def import_expenses(
    group_id: str,
    file: UploadFile = File(...),
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Import expenses from CSV file"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Read CSV content
    content = await file.read()
    csv_content = content.decode("utf-8")
    
    # Parse CSV
    importer = CSVImporter()
    parsed_expenses, anomalies = importer.parse_csv(csv_content)
    
    # Create import report
    import_report = ImportReport(
        id=str(uuid.uuid4()),
        group_id=group_id,
        total_rows=importer.processed_rows,
        successful_imports=len(parsed_expenses),
        anomalies_detected=json.dumps([a.to_dict() for a in anomalies]),
        created_by=current_user.id
    )
    
    db.add(import_report)
    db.flush()
    
    # Import expenses
    for exp_data in parsed_expenses:
        # Find or create users by name
        payer = None
        for member in group.members:
            if (member.full_name and member.full_name.lower() == exp_data["paid_by"].lower()) or \
               member.username.lower() == exp_data["paid_by"].lower():
                payer = member
                break
        
        if not payer:
            # Skip if payer not found
            continue
        
        expense = Expense(
            id=exp_data["id"],
            group_id=group_id,
            description=exp_data["description"],
            amount=exp_data["amount"],
            currency=exp_data["currency"],
            paid_by_user_id=payer.id,
            split_type=exp_data["split_type"],
            expense_date=exp_data["expense_date"],
            notes=exp_data["notes"],
            csv_row_number=exp_data["csv_row_number"]
        )
        
        db.add(expense)
        db.flush()
        
        # Create splits
        split_details = exp_data.get("split_details", {})
        for member in group.members:
            member_name = member.full_name or member.username
            
            if member_name.lower() in [s.lower() for s in exp_data["split_with"]]:
                split = ExpenseSplit(
                    id=str(uuid.uuid4()),
                    expense_id=expense.id,
                    user_id=member.id,
                    amount=split_details.get(member_name, 0) if exp_data["split_type"] == "unequal" else 0,
                    percentage=split_details.get(member_name, 0) if exp_data["split_type"] == "percentage" else None,
                    shares=split_details.get(member_name, 1) if exp_data["split_type"] == "share" else None
                )
                db.add(split)
    
    db.commit()
    
    # Return report
    return {
        "import_id": import_report.id,
        "total_rows": import_report.total_rows,
        "successful_imports": import_report.successful_imports,
        "anomalies": [a.to_dict() for a in anomalies]
    }


@router.get("/groups/{group_id}/import-report/{report_id}", response_model=ImportReportResponse)
async def get_import_report(
    group_id: str,
    report_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get import report details"""
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
    """Get all expenses in a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    expenses = db.query(Expense).filter(
        Expense.group_id == group_id,
        Expense.is_deleted == False
    ).all()
    
    return [ExpenseResponse.model_validate(e) for e in expenses]


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
