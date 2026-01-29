from typing import Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlmodel import Session, select, and_, or_
from app.db.session import get_session
from app.models.appointment import Appointment, AppointmentCreate, AppointmentRead, AppointmentStatus, AppointmentUpdate
from app.models.availability import Availability
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user, check_role

from app.core.mail import send_new_appointment_email

router = APIRouter()

async def send_notification(email: str, subject: str, message: str):
    # Real notification logic using fastapi-mail
    await send_new_appointment_email(email, subject, message)

def is_staff_available(session: Session, staff_id: int, start_time: datetime, end_time: datetime) -> bool:
    # 1. Check if there's an overlapping appointment
    overlapping_appointment = session.exec(
        select(Appointment).where(
            and_(
                Appointment.staff_id == staff_id,
                Appointment.status == AppointmentStatus.SCHEDULED,
                or_(
                    and_(Appointment.start_time <= start_time, Appointment.end_time > start_time),
                    and_(Appointment.start_time < end_time, Appointment.end_time >= end_time),
                    and_(Appointment.start_time >= start_time, Appointment.end_time <= end_time)
                )
            )
        )
    ).first()
    
    if overlapping_appointment:
        return False

    # 2. Check if it's within staff availability
    day_of_week = start_time.weekday()
    specific_date = start_time.date()
    start_time_only = start_time.time()
    end_time_only = end_time.time()

    availabilities = session.exec(
        select(Availability).where(
            and_(
                Availability.staff_id == staff_id,
                or_(
                    Availability.specific_date == specific_date,
                    and_(Availability.day_of_week == day_of_week, Availability.is_recurring == True)
                )
            )
        )
    ).all()

    for avail in availabilities:
        if avail.start_time <= start_time_only and avail.end_time >= end_time_only:
            return True
            
    return False

@router.post("/", response_model=AppointmentRead)
def create_appointment(
    *,
    session: Session = Depends(get_session),
    appointment_in: AppointmentCreate,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    if not is_staff_available(session, appointment_in.staff_id, appointment_in.start_time, appointment_in.end_time):
        raise HTTPException(status_code=400, detail="Staff is not available at this time")
    
    db_obj = Appointment(
        start_time=appointment_in.start_time,
        end_time=appointment_in.end_time,
        notes=appointment_in.notes,
        client_id=current_user.id,
        staff_id=appointment_in.staff_id,
        status=AppointmentStatus.SCHEDULED
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    
    # Send notifications
    background_tasks.add_task(send_notification, current_user.email, "Appointment Confirmed", f"Your appointment is confirmed for {db_obj.start_time}")
    staff = session.get(User, db_obj.staff_id)
    if staff:
        background_tasks.add_task(send_notification, staff.email, "New Appointment Booked", f"New appointment booked for {db_obj.start_time}")
        
    return db_obj

@router.get("/", response_model=List[AppointmentRead])
def read_appointments(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    query = select(Appointment)
    # RBAC: Clients see only their own, Staff see their own, Admin see all
    if current_user.role == UserRole.CLIENT:
        query = query.where(Appointment.client_id == current_user.id)
    elif current_user.role == UserRole.STAFF:
        query = query.where(Appointment.staff_id == current_user.id)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@router.patch("/{id}", response_model=AppointmentRead)
def update_appointment(
    *,
    session: Session = Depends(get_session),
    id: int,
    appointment_in: AppointmentUpdate,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    db_obj = session.get(Appointment, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Permission check
    if current_user.role != UserRole.ADMIN and db_obj.client_id != current_user.id and db_obj.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Enforcement policy: Cannot cancel/reschedule within 2 hours of appointment (example)
    if db_obj.start_time - datetime.utcnow() < timedelta(hours=2):
         raise HTTPException(status_code=400, detail="Cannot change appointment within 2 hours of start time")

    update_data = appointment_in.dict(exclude_unset=True)
    for field in update_data:
        setattr(db_obj, field, update_data[field])
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    
    background_tasks.add_task(send_notification, current_user.email, "Appointment Updated", f"Your appointment on {db_obj.start_time} has been updated to {db_obj.status}")
    
    return db_obj
