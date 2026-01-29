from datetime import datetime

def get_appointment_confirmed_template(client_name: str, staff_name: str, start_time: datetime, end_time: datetime) -> str:
    """HTML template for appointment confirmation email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .appointment-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #4CAF50; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
            .button {{ display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; margin: 10px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✓ Appointment Confirmed</h1>
            </div>
            <div class="content">
                <p>Hello {client_name},</p>
                <p>Your appointment has been successfully scheduled!</p>
                
                <div class="appointment-details">
                    <h3>Appointment Details</h3>
                    <p><strong>Staff:</strong> {staff_name}</p>
                    <p><strong>Date:</strong> {start_time.strftime('%B %d, %Y')}</p>
                    <p><strong>Time:</strong> {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}</p>
                </div>
                
                <p>You will receive a reminder 24 hours before your appointment.</p>
                <p>If you need to reschedule or cancel, please contact us at least 2 hours in advance.</p>
            </div>
            <div class="footer">
                <p>This is an automated message from the Appointment Scheduling System</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_appointment_reminder_template(client_name: str, staff_name: str, start_time: datetime, end_time: datetime) -> str:
    """HTML template for appointment reminder email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #FF9800; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .appointment-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #FF9800; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>⏰ Appointment Reminder</h1>
            </div>
            <div class="content">
                <p>Hello {client_name},</p>
                <p>This is a friendly reminder about your upcoming appointment tomorrow.</p>
                
                <div class="appointment-details">
                    <h3>Appointment Details</h3>
                    <p><strong>Staff:</strong> {staff_name}</p>
                    <p><strong>Date:</strong> {start_time.strftime('%B %d, %Y')}</p>
                    <p><strong>Time:</strong> {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}</p>
                </div>
                
                <p>Please arrive 5-10 minutes early.</p>
                <p>If you need to reschedule or cancel, please contact us as soon as possible.</p>
            </div>
            <div class="footer">
                <p>This is an automated message from the Appointment Scheduling System</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_appointment_rescheduled_template(client_name: str, staff_name: str, old_time: datetime, new_start_time: datetime, new_end_time: datetime) -> str:
    """HTML template for appointment rescheduled email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2196F3; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .appointment-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #2196F3; }}
            .old-time {{ text-decoration: line-through; color: #999; }}
            .new-time {{ color: #2196F3; font-weight: bold; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📅 Appointment Rescheduled</h1>
            </div>
            <div class="content">
                <p>Hello {client_name},</p>
                <p>Your appointment has been rescheduled.</p>
                
                <div class="appointment-details">
                    <h3>Updated Appointment Details</h3>
                    <p><strong>Staff:</strong> {staff_name}</p>
                    <p class="old-time"><strong>Previous Time:</strong> {old_time.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p class="new-time"><strong>New Time:</strong> {new_start_time.strftime('%B %d, %Y at %I:%M %p')} - {new_end_time.strftime('%I:%M %p')}</p>
                </div>
                
                <p>You will receive a reminder 24 hours before your appointment.</p>
            </div>
            <div class="footer">
                <p>This is an automated message from the Appointment Scheduling System</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_appointment_cancelled_template(client_name: str, staff_name: str, start_time: datetime) -> str:
    """HTML template for appointment cancellation email"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f44336; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .appointment-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #f44336; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>✕ Appointment Cancelled</h1>
            </div>
            <div class="content">
                <p>Hello {client_name},</p>
                <p>Your appointment has been cancelled.</p>
                
                <div class="appointment-details">
                    <h3>Cancelled Appointment</h3>
                    <p><strong>Staff:</strong> {staff_name}</p>
                    <p><strong>Date:</strong> {start_time.strftime('%B %d, %Y')}</p>
                    <p><strong>Time:</strong> {start_time.strftime('%I:%M %p')}</p>
                </div>
                
                <p>If you'd like to schedule a new appointment, please contact us.</p>
            </div>
            <div class="footer">
                <p>This is an automated message from the Appointment Scheduling System</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_staff_new_appointment_template(staff_name: str, client_name: str, start_time: datetime, end_time: datetime, notes: str = None) -> str:
    """HTML template for staff notification about new appointment"""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #673AB7; color: white; padding: 20px; text-align: center; }}
            .content {{ background-color: #f9f9f9; padding: 20px; margin: 20px 0; border-radius: 5px; }}
            .appointment-details {{ background-color: white; padding: 15px; margin: 15px 0; border-left: 4px solid #673AB7; }}
            .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📋 New Appointment Booked</h1>
            </div>
            <div class="content">
                <p>Hello {staff_name},</p>
                <p>A new appointment has been scheduled with you.</p>
                
                <div class="appointment-details">
                    <h3>Appointment Details</h3>
                    <p><strong>Client:</strong> {client_name}</p>
                    <p><strong>Date:</strong> {start_time.strftime('%B %d, %Y')}</p>
                    <p><strong>Time:</strong> {start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}</p>
                    {f'<p><strong>Notes:</strong> {notes}</p>' if notes else ''}
                </div>
            </div>
            <div class="footer">
                <p>This is an automated message from the Appointment Scheduling System</p>
            </div>
        </div>
    </body>
    </html>
    """
