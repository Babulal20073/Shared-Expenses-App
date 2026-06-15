import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from schemas import GroupCreate, GroupUpdate, GroupResponse, UserResponse
from services.auth_service import GroupService, AuthService
from middleware.auth import get_current_user
from models.models import Group
import uuid

router = APIRouter(prefix="/api/groups", tags=["groups"])


@router.post("/", response_model=GroupResponse)
async def create_group(
    group_data: GroupCreate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new group"""
    group = GroupService.create_group(group_data, current_user.id, db)
    return GroupResponse.model_validate(group)


@router.get("/", response_model=List[GroupResponse])
async def get_user_groups(
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all groups for current user"""
    groups = GroupService.get_user_groups(current_user.id, db)
    return [GroupResponse.model_validate(g) for g in groups]


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    # Check if user is a member
    members = GroupService.get_group_members(group_id, db)
    if current_user.id not in [m.id for m in members]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a member of this group")
    
    return GroupResponse.model_validate(group)


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: str,
    group_data: GroupUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    if group.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can update group")
    
    if group_data.name:
        group.name = group_data.name
    if group_data.description is not None:
        group.description = group_data.description
    
    db.commit()
    db.refresh(group)
    
    return GroupResponse.model_validate(group)


@router.post("/{group_id}/members/{user_email}")
async def add_member(
    group_id: str,
    user_email: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a member to a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    if group.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can add members")
    
    user = AuthService.get_user_by_email(user_email, db)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    try:
        GroupService.add_member_to_group(group_id, user.id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": "Member added successfully"}


@router.delete("/{group_id}/members/{user_id}")
async def remove_member(
    group_id: str,
    user_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Remove a member from a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    if group.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only creator can remove members")
    
    try:
        GroupService.remove_member_from_group(group_id, user_id, db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    return {"message": "Member removed successfully"}


from models.models import GroupMember, User
from pydantic import BaseModel
from datetime import datetime

class MemberTimelineUpdate(BaseModel):
    joined_at: datetime
    left_at: Optional[datetime] = None

@router.get("/{group_id}/members", response_model=List[UserResponse])
async def get_members(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all members of a group"""
    group = db.query(Group).filter(Group.id == group_id).first()
    
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    
    members = GroupService.get_group_members(group_id, db)
    return [UserResponse.model_validate(m) for m in members]


@router.get("/{group_id}/members-detailed")
async def get_members_detailed(
    group_id: str,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all group members with detailed timeline information"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        
    members_data = db.query(
        User.id, User.username, User.email, User.full_name,
        GroupMember.joined_at, GroupMember.left_at, GroupMember.is_active
    ).join(
        GroupMember, User.id == GroupMember.user_id
    ).filter(
        GroupMember.group_id == group_id
    ).all()
    
    return [
        {
            "user_id": m[0],
            "username": m[1],
            "email": m[2],
            "full_name": m[3],
            "joined_at": m[4].isoformat() if m[4] else None,
            "left_at": m[5].isoformat() if m[5] else None,
            "is_active": m[6]
        }
        for m in members_data
    ]


@router.put("/{group_id}/members/{user_id}/timeline")
async def update_member_timeline(
    group_id: str,
    user_id: str,
    timeline_data: MemberTimelineUpdate,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a member's active join/leave timeline"""
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
        
    if group.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only group creator can edit timeline")
        
    member = db.query(GroupMember).filter(
        GroupMember.group_id == group_id,
        GroupMember.user_id == user_id
    ).first()
    
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in group")
        
    member.joined_at = timeline_data.joined_at
    member.left_at = timeline_data.left_at
    
    db.commit()
    return {"message": "Timeline updated successfully"}

