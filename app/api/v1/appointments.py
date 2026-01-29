from typing import Any, List
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import Response
from sqlmodel import Session, select, and_, or_
from ics import Calendar, Event
from app.db.session import get_session
from app.models.appointment import Appointment, AppointmentCreate, AppointmentRead, AppointmentStatus, AppointmentUpdate, AppointmentReschedule
from app.models.availability import Availability
from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user, check_role

from app.core.mail import send_new_appointment_email
from app.core.email_templates import (
    get_appointment_confirmed_template,
    get_staff_new_appointment_template,
    get_appointment_rescheduled_template
)

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
    # Check if client is blocked due to no-shows
    if current_user.is_blocked:
        raise HTTPException(
            status_code=403, 
            detail=f"You are blocked from booking appointments due to {current_user.no_show_count} no-shows. Please contact support."
        )
    
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
    
    # Send notifications with HTML templates
    staff = session.get(User, db_obj.staff_id)
    
    client_html = get_appointment_confirmed_template(
        client_name=current_user.full_name or current_user.email,
        staff_name=staff.full_name or staff.email if staff else "Staff",
        start_time=db_obj.start_time,
        end_time=db_obj.end_time
    )
    background_tasks.add_task(send_notification, current_user.email, "Appointment Confirmed", client_html)
    
    if staff:
        staff_html = get_staff_new_appointment_template(
            staff_name=staff.full_name or staff.email,
            client_name=current_user.full_name or current_user.email,
            start_time=db_obj.start_time,
            end_time=db_obj.end_time,
            notes=db_obj.notes
        )
        background_tasks.add_task(send_notification, staff.email, "New Appointment Booked", staff_html)
        
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

@router.post("/{id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    *,
    session: Session = Depends(get_session),
    id: int,
    reschedule_data: AppointmentReschedule,
    current_user: User = Depends(get_current_user),
    background_tasks: BackgroundTasks
) -> Any:
    """
    Reschedule an existing appointment to a new time slot.
    Validates availability and enforces cancellation policies.
    """
    db_obj = session.get(Appointment, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Permission check - only client or staff involved in appointment can reschedule
    if current_user.role != UserRole.ADMIN and db_obj.client_id != current_user.id and db_obj.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Cannot reschedule cancelled or completed appointments
    if db_obj.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Cannot reschedule {db_obj.status} appointment")
    
    # Enforcement policy: Cannot reschedule within 2 hours of appointment
    if db_obj.start_time - datetime.utcnow() < timedelta(hours=2):
        raise HTTPException(status_code=400, detail="Cannot reschedule within 2 hours of start time")
    
    # Check if staff is available at the new time (excluding this appointment)
    overlapping_appointment = session.exec(
        select(Appointment).where(
            and_(
                Appointment.staff_id == db_obj.staff_id,
                Appointment.id != id,
                Appointment.status == AppointmentStatus.SCHEDULED,
                or_(
                    and_(Appointment.start_time <= reschedule_data.new_start_time, Appointment.end_time > reschedule_data.new_start_time),
                    and_(Appointment.start_time < reschedule_data.new_end_time, Appointment.end_time >= reschedule_data.new_end_time),
                    and_(Appointment.start_time >= reschedule_data.new_start_time, Appointment.end_time <= reschedule_data.new_end_time)
                )
            )
        )
    ).first()
    
    if overlapping_appointment:
        raise HTTPException(status_code=400, detail="Staff is not available at the new time")
    
    # Check staff availability window
    day_of_week = reschedule_data.new_start_time.weekday()
    specific_date = reschedule_data.new_start_time.date()
    start_time_only = reschedule_data.new_start_time.time()
    end_time_only = reschedule_data.new_end_time.time()
    
    availabilities = session.exec(
        select(Availability).where(
            and_(
                Availability.staff_id == db_obj.staff_id,
                or_(
                    Availability.specific_date == specific_date,
                    and_(Availability.day_of_week == day_of_week, Availability.is_recurring == True)
                )
            )
        )
    ).all()
    
    is_within_availability = False
    for avail in availabilities:
        if avail.start_time <= start_time_only and avail.end_time >= end_time_only:
            is_within_availability = True
            break
    
    if not is_within_availability:
        raise HTTPException(status_code=400, detail="New time is outside staff availability hours")
    
    # Store old time for notification
    old_start_time = db_obj.start_time
    
    # Update appointment
    db_obj.start_time = reschedule_data.new_start_time
    db_obj.end_time = reschedule_data.new_end_time
    if reschedule_data.reason:
        db_obj.notes = f"{db_obj.notes or ''}\n[Rescheduled: {reschedule_data.reason}]"
    
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    
    # Send notifications to both client and staff with HTML templates
    client = session.get(User, db_obj.client_id)
    staff = session.get(User, db_obj.staff_id)
    
    if client and staff:
        client_html = get_appointment_rescheduled_template(
            client_name=client.full_name or client.email,
            staff_name=staff.full_name or staff.email,
            old_time=old_start_time,
            new_start_time=db_obj.start_time,
            new_end_time=db_obj.end_time
        )
        background_tasks.add_task(
            send_notification, 
            client.email, 
            "Appointment Rescheduled", 
            client_html
        )
        
        staff_html = get_appointment_rescheduled_template(
            client_name=client.full_name or client.email,
            staff_name=staff.full_name or staff.email,
            old_time=old_start_time,
            new_start_time=db_obj.start_time,
            new_end_time=db_obj.end_time
        )
        background_tasks.add_task(
            send_notification, 
            staff.email, 
            "Appointment Rescheduled", 
            staff_html
        )
    
    return db_obj

@router.get("/{id}/export.ics")
def export_appointment_ical(
    *,
    session: Session = Depends(get_session),
    id: int,
    current_user: User = Depends(get_current_user)
) -> Response:
    """
    Export a single appointment as an iCalendar (.ics) file.
    Can be imported into Google Calendar, Apple Calendar, Outlook, etc.
    """
    db_obj = session.get(Appointment, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Permission check
    if current_user.role != UserRole.ADMIN and db_obj.client_id != current_user.id and db_obj.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Get client and staff details
    client = session.get(User, db_obj.client_id)
    staff = session.get(User, db_obj.staff_id)
    
    # Create calendar and event
    cal = Calendar()
    event = Event()
    event.name = f"Appointment with {staff.full_name or staff.email if staff else 'Staff'}"
    event.begin = db_obj.start_time
    event.end = db_obj.end_time
    event.description = db_obj.notes or "No additional notes"
    event.location = "To be determined"
    # Map internal status to iCal status
    status_map = {
        AppointmentStatus.SCHEDULED: "CONFIRMED",
        AppointmentStatus.CANCELLED: "CANCELLED",
        AppointmentStatus.COMPLETED: "CONFIRMED",
        AppointmentStatus.NO_SHOW: "CANCELLED"
    }
    event.status = status_map.get(db_obj.status, "CONFIRMED")
    
    if client and staff:
        event.organizer = f"{staff.full_name or staff.email} <{staff.email}>"
        event.add_attendee(f"{client.full_name or client.email} <{client.email}>")
    
    cal.events.add(event)
    
    # Return as downloadable .ics file
    return Response(
        content=str(cal),
        media_type="text/calendar",
        headers={
            "Content-Disposition": f"attachment; filename=appointment_{id}.ics"
        }
    )

@router.get("/export-all.ics")
def export_all_appointments_ical(
    *,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user)
) -> Response:
    """
    Export all user's appointments as a single iCalendar (.ics) file.
    """
    query = select(Appointment)
    
    # RBAC: Clients see only their own, Staff see their own, Admin see all
    if current_user.role == UserRole.CLIENT:
        query = query.where(Appointment.client_id == current_user.id)
    elif current_user.role == UserRole.STAFF:
        query = query.where(Appointment.staff_id == current_user.id)
    
    appointments = session.exec(query).all()
    
    # Collect all user IDs to fetch in batch
    user_ids = set()
    for appointment in appointments:
        user_ids.add(appointment.client_id)
        user_ids.add(appointment.staff_id)
    
    # Fetch users in one query
    users = session.exec(select(User).where(User.id.in_(user_ids))).all()
    user_map = {user.id: user for user in users}
    
    # Create calendar
    cal = Calendar()
    cal.creator = f"Appointment Scheduling System - {current_user.email}"
    
    for appointment in appointments:
        client = user_map.get(appointment.client_id)
        staff = user_map.get(appointment.staff_id)
        
        event = Event()
        event.name = f"Appointment with {staff.full_name or staff.email if staff else 'Staff'}"
        event.begin = appointment.start_time
        event.end = appointment.end_time
        event.description = appointment.notes or "No additional notes"
        # Map internal status to iCal status
        status_map = {
            AppointmentStatus.SCHEDULED: "CONFIRMED",
            AppointmentStatus.CANCELLED: "CANCELLED",
            AppointmentStatus.COMPLETED: "CONFIRMED",
            AppointmentStatus.NO_SHOW: "CANCELLED"
        }
        event.status = status_map.get(appointment.status, "CONFIRMED")
        
        if client and staff:
            event.organizer = f"{staff.full_name or staff.email} <{staff.email}>"
            event.add_attendee(f"{client.full_name or client.email} <{client.email}>")
        
        cal.events.add(event)
    
    # Return as downloadable .ics file
    return Response(
        content=str(cal),
        media_type="text/calendar",
        headers={
            "Content-Disposition": "attachment; filename=all_appointments.ics"
        }
    )

@router.post("/{id}/mark-no-show", response_model=AppointmentRead)
def mark_appointment_no_show(
    *,
    session: Session = Depends(get_session),
    id: int,
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.STAFF]))
) -> Any:
    """
    Mark an appointment as no-show. Only staff and admin can do this.
    Increments the client's no-show count and may block them after 3 no-shows.
    """
    db_obj = session.get(Appointment, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Only staff assigned to this appointment or admin can mark no-show
    if current_user.role != UserRole.ADMIN and db_obj.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Can only mark scheduled appointments as no-show
    if db_obj.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Cannot mark {db_obj.status} appointment as no-show")
    
    # Check if appointment time has passed
    if db_obj.start_time > datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot mark future appointment as no-show")
    
    # Update appointment status
    db_obj.status = AppointmentStatus.NO_SHOW
    session.add(db_obj)
    
    # Update client's no-show count
    client = session.get(User, db_obj.client_id)
    if client:
        client.no_show_count += 1
        
        # Policy: Block client after 3 no-shows
        if client.no_show_count >= 3:
            client.is_blocked = True
            print(f"[Policy] Client {client.email} has been blocked due to {client.no_show_count} no-shows")
        
        session.add(client)
    
    session.commit()
    session.refresh(db_obj)
    
    return db_obj

@router.post("/{id}/mark-completed", response_model=AppointmentRead)
def mark_appointment_completed(
    *,
    session: Session = Depends(get_session),
    id: int,
    current_user: User = Depends(check_role([UserRole.ADMIN, UserRole.STAFF]))
) -> Any:
    """
    Mark an appointment as completed. Only staff and admin can do this.
    """
    db_obj = session.get(Appointment, id)
    if not db_obj:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Only staff assigned to this appointment or admin can mark completed
    if current_user.role != UserRole.ADMIN and db_obj.staff_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    # Can only mark scheduled appointments as completed
    if db_obj.status != AppointmentStatus.SCHEDULED:
        raise HTTPException(status_code=400, detail=f"Cannot mark {db_obj.status} appointment as completed")
    
    # Check if appointment time has passed
    if db_obj.start_time > datetime.utcnow():
        raise HTTPException(status_code=400, detail="Cannot mark future appointment as completed")
    
    db_obj.status = AppointmentStatus.COMPLETED
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    
    return db_obj
