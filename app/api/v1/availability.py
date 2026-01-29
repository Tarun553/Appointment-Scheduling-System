from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.db.session import get_session
from app.models.availability import Availability, AvailabilityCreate, AvailabilityRead
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user, check_role

router = APIRouter()

@router.post("/", response_model=AvailabilityRead)
def create_availability(
    *,
    session: Session = Depends(get_session),
    availability_in: AvailabilityCreate,
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.STAFF]))
) -> Any:
    # If not admin, can only set their own availability
    if current_user.role != UserRole.ADMIN and availability_in.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db_obj = Availability.from_orm(availability_in)
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj

@router.get("/", response_model=List[AvailabilityRead])
def read_availabilities(
    *,
    session: Session = Depends(get_session),
    staff_id: int = None,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Availability)
    if staff_id:
        query = query.where(Availability.staff_id == staff_id)
    return session.exec(query.offset(skip).limit(limit)).all()
