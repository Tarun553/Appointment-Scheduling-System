from typing import Any, List
from datetime import datetime, date, time, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select, and_, or_
from app.db.session import get_session
from app.models.availability import Availability, AvailabilityCreate, AvailabilityRead
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user, check_role
from pydantic import BaseModel

router = APIRouter()

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime

class AvailableSlotsResponse(BaseModel):
    date: date
    staff_id: int
    slots: List[TimeSlot]

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
    
    db_obj = Availability(**availability_in.dict())
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

@router.get("/slots", response_model=AvailableSlotsResponse)
def get_available_slots(
    *,
    session: Session = Depends(get_session),
    staff_id: int = Query(..., description="Staff member ID"),
    date_param: date = Query(..., alias="date", description="Date to check availability (YYYY-MM-DD)"),
    slot_duration: int = Query(60, ge=1, le=480, description="Duration of each slot in minutes(1-480)")
) -> Any:
    """
    Get available time slots for a staff member on a specific date.
    Returns slots that are within staff availability and not already booked.
    """
    day_of_week = date_param.weekday()
    
    # Get staff availability for this date
    availabilities = session.exec(
        select(Availability).where(
            and_(
                Availability.staff_id == staff_id,
                or_(
                    Availability.specific_date == date_param,
                    and_(Availability.day_of_week == day_of_week, Availability.is_recurring == True)
                )
            )
        )
    ).all()
    
    if not availabilities:
        return AvailableSlotsResponse(date=date_param, staff_id=staff_id, slots=[])
    
    # Get all booked appointments for this staff on this date
    start_of_day = datetime.combine(date_param, time.min)
    end_of_day = datetime.combine(date_param, time.max)
    
    booked_appointments = session.exec(
        select(Appointment).where(
            and_(
                Appointment.staff_id == staff_id,
                Appointment.status == AppointmentStatus.SCHEDULED,
                Appointment.start_time < end_of_day,
                Appointment.end_time > start_of_day
            )
        )
    ).all()
    
    # Generate available slots
    available_slots = []
    slot_delta = timedelta(minutes=slot_duration)
    
    for avail in availabilities:
        current_time = datetime.combine(date_param, avail.start_time)
        end_time = datetime.combine(date_param, avail.end_time)
        
        while current_time + slot_delta <= end_time:
            slot_end = current_time + slot_delta
            
            # Check if this slot overlaps with any booked appointment
            is_available = True
            for appt in booked_appointments:
                if not (slot_end <= appt.start_time or current_time >= appt.end_time):
                    is_available = False
                    break
            
            if is_available:
                available_slots.append(TimeSlot(start_time=current_time, end_time=slot_end))
            
            current_time = slot_end
    
    return AvailableSlotsResponse(date=date_param, staff_id=staff_id, slots=available_slots)
