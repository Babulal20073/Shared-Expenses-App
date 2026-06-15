import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from schemas import GroupBalance, SettlementSummary
from middleware.auth import get_current_user
from models.models import Group
from services.expense_service import ExpenseService

router = APIRouter(prefix="/api/groups/{group_id}/balances", tags=["balances"])


@router.get("", response_model=List[GroupBalance])
async def get_group_balances(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get balance summary for all members in a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    balances_dict = ExpenseService.calculate_group_balances(group_id, db)
    
    result = []
    for user_id, balance_info in balances_dict.items():
        user = balance_info["user"]
        result.append({
            "user_id": user_id,
            "user_name": user.full_name or user.username,
            "owes_amount": round(balance_info["owes"], 2),
            "owed_by_amount": round(balance_info["owed"], 2),
            "net_balance": round(balance_info["net"], 2)
        })
    
    return result


@router.get("/settlement", response_model=List[SettlementSummary])
async def get_settlement_plan(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get settlement plan to clear all debts"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    settlements = ExpenseService.get_settlement_summary(group_id, db)
    
    return [
        {
            "from_user": s["from_user"],
            "to_user": s["to_user"],
            "amount": s["amount"],
            "currency": "INR"
        }
        for s in settlements
    ]
