from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlmodel import Session, select, and_
import asyncio

from app.db.session import SessionLocal
from app.models.appointment import Appointment, AppointmentStatus
from app.models.user import User
from app.core.mail import send_new_appointment_email
from app.core.email_templates import get_appointment_reminder_template

scheduler = AsyncIOScheduler()

async def send_appointment_reminders():
    """
    Check for appointments scheduled 24 hours from now and send reminders.
    This function runs periodically (e.g., every hour).
    """
    session = SessionLocal()
    try:
        # Calculate time window: 24 hours from now +/- 1 hour buffer
        now = datetime.utcnow()
        reminder_start = now + timedelta(hours=23)
        reminder_end = now + timedelta(hours=25)
        
        # Get all scheduled appointments within the reminder window
        appointments = session.exec(
            select(Appointment).where(
                and_(
                    Appointment.status == AppointmentStatus.SCHEDULED,
                    Appointment.start_time >= reminder_start,
                    Appointment.start_time <= reminder_end
                )
            )
        ).all()
        
        print(f"[Reminder Scheduler] Found {len(appointments)} appointments to remind")
        
        for appointment in appointments:
            # Get client and staff details
            client = session.get(User, appointment.client_id)
            staff = session.get(User, appointment.staff_id)
            
            if client and staff:
                # Generate HTML reminder email
                html_content = get_appointment_reminder_template(
                    client_name=client.full_name or client.email,
                    staff_name=staff.full_name or staff.email,
                    start_time=appointment.start_time,
                    end_time=appointment.end_time
                )
                
                # Send reminder email
                try:
                    await send_new_appointment_email(
                        client.email,
                        "⏰ Appointment Reminder - Tomorrow",
                        html_content
                    )
                    print(f"[Reminder Scheduler] Sent reminder to {client.email} for appointment #{appointment.id}")
                except Exception as e:
                    print(f"[Reminder Scheduler] Failed to send reminder for appointment #{appointment.id}: {e}")
    
    except Exception as e:
        print(f"[Reminder Scheduler] Error in send_appointment_reminders: {e}")
    finally:
        session.close()

def start_scheduler():
    """Start the background scheduler"""
    # Run reminder check every hour
    scheduler.add_job(
        send_appointment_reminders,
        trigger=IntervalTrigger(hours=1),
        id='appointment_reminders',
        name='Send appointment reminders',
        replace_existing=True
    )
    
    scheduler.start()
    print("[Reminder Scheduler] Started - checking for reminders every hour")

def shutdown_scheduler():
    """Shutdown the scheduler"""
    if scheduler.running:
        scheduler.shutdown()
        print("[Reminder Scheduler] Shutdown complete")
