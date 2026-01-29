# Appointment Scheduling System

A comprehensive backend API for booking and managing appointments with availability control, automated reminders, and calendar integration.

## Features

- **User Authentication & Authorization**
  - JWT-based authentication
  - Role-based access control (Admin, Staff, Client)
  - Secure password hashing

- **Availability Management**
  - Recurring weekly availability slots
  - Specific date availability
  - Query available time slots for booking

- **Appointment Booking**
  - Book appointments with availability validation
  - Prevent double-booking
  - View appointments (role-filtered)
  - Reschedule appointments
  - Cancel appointments with policy enforcement
  - Mark appointments as completed or no-show

- Automated Email Notifications
  - HTML email templates
  - Confirmation emails on booking
  - Reminder emails 24 hours before appointment
  - Rescheduling notifications

- Calendar Integration
  - Export individual appointments as .ics files
  - Export all appointments as .ics calendar
  - Import into Google Calendar, Apple Calendar, Outlook, etc.

- Policy Enforcement
  - 2-hour cancellation/reschedule policy
  - No-show tracking
  - Automatic blocking after 3 no-shows
  - Completed appointment tracking

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLite (via SQLModel ORM)
- **Authentication**: JWT (python-jose)
- **Email**: FastAPI-Mail (SMTP)
- **Scheduler**: APScheduler
- **Calendar**: ics (iCalendar format)

## Installation

### Prerequisites

- Python 3.8+
- pip

### Setup

1. Clone the repository:
```bash
cd appointment
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables in `.env`:
```env
PROJECT_NAME="Appointment Scheduling System"
API_V1_STR="/api/v1"
SECRET_KEY="your-secret-key-here"
ACCESS_TOKEN_EXPIRE_MINUTES=11520
DATABASE_URL="sqlite:///./appointment.db"

# Email Configuration (Gmail example)
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=your-email@gmail.com
MAIL_PORT=587
MAIL_SERVER=smtp.gmail.com
MAIL_FROM_NAME="Appointment System"
MAIL_TLS=True
MAIL_SSL=False
USE_CREDENTIALS=True
```

4. Run the application:
```bash
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## API Endpoints

### Authentication

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/auth/register` | Register a new user | No |
| POST | `/api/v1/auth/login` | Login and get access token | No |
| GET | `/api/v1/auth/me` | Get current user info | Yes |

### Availability

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/availability/` | Create availability slot | Staff/Admin |
| GET | `/api/v1/availability/` | List availability slots | No |
| GET | `/api/v1/availability/slots` | Get available time slots | No |

### Appointments

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/appointments/` | Book an appointment | Yes |
| GET | `/api/v1/appointments/` | List appointments | Yes |
| PATCH | `/api/v1/appointments/{id}` | Update appointment | Yes |
| POST | `/api/v1/appointments/{id}/reschedule` | Reschedule appointment | Yes |
| POST | `/api/v1/appointments/{id}/mark-no-show` | Mark as no-show | Staff/Admin |
| POST | `/api/v1/appointments/{id}/mark-completed` | Mark as completed | Staff/Admin |
| GET | `/api/v1/appointments/{id}/export.ics` | Export appointment as iCal | Yes |
| GET | `/api/v1/appointments/export-all.ics` | Export all appointments | Yes |

## Usage Examples

### 1. Register a User

```bash
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "staff@example.com",
    "full_name": "John Staff",
    "password": "password123",
    "role": "staff"
  }'
```

### 2. Login

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=staff@example.com&password=password123"
```

Response:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### 3. Set Staff Availability

```bash
curl -X POST "http://localhost:8000/api/v1/availability/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "day_of_week": 0,
    "start_time": "09:00:00",
    "end_time": "17:00:00",
    "is_recurring": true,
    "staff_id": 1
  }'
```

### 4. Get Available Slots

```bash
curl "http://localhost:8000/api/v1/availability/slots?staff_id=1&date=2026-02-02&slot_duration=60"
```

### 5. Book an Appointment

```bash
curl -X POST "http://localhost:8000/api/v1/appointments/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "staff_id": 1,
    "start_time": "2026-02-02T10:00:00",
    "end_time": "2026-02-02T11:00:00",
    "notes": "Initial consultation"
  }'
```

### 6. Reschedule an Appointment

```bash
curl -X POST "http://localhost:8000/api/v1/appointments/1/reschedule" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "new_start_time": "2026-02-03T14:00:00",
    "new_end_time": "2026-02-03T15:00:00",
    "reason": "Schedule conflict"
  }'
```

### 7. Export Appointment to Calendar

```bash
curl "http://localhost:8000/api/v1/appointments/1/export.ics" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o appointment.ics
```

## User Roles

### Client
- Book appointments
- View their own appointments
- Reschedule/cancel appointments
- Export appointments to calendar
- Blocked automatically after 3 no-shows

### Staff
- Set their own availability
- View appointments assigned to them
- Mark appointments as completed or no-show
- Export their appointments

### Admin
- Full access to all appointments
- Manage all availabilities
- View all users
- Override policies

## Automated Features

### Email Reminders
- Automatically sends reminder emails 24 hours before appointments
- Runs every hour to check for upcoming appointments
- Uses HTML email templates

### No-Show Policy
- Tracks no-show count per client
- Automatically blocks clients after 3 no-shows
- Blocked clients cannot book new appointments

### Cancellation Policy
- Cannot cancel/reschedule within 2 hours of appointment start time
- Only scheduled appointments can be modified

## Database Schema

### User
- id, email, full_name, role, is_active
- hashed_password
- no_show_count, is_blocked

### Appointment
- id, start_time, end_time, notes, status
- client_id, staff_id

### Availability
- id, day_of_week, specific_date
- start_time, end_time, is_recurring
- staff_id

## Development

### Run Tests
```bash
pytest tests/
```

### Database Migration
The database is automatically initialized on startup. To reset:
```bash
rm appointment.db

## Postman Collection

Import `appointment_scheduling.postman_collection.json` into Postman for pre-configured API requests.

## Troubleshooting

### Email not sending
- Verify SMTP credentials in `.env`
- For Gmail, use an App Password (not regular password)
- Enable "Less secure app access" or use OAuth2

### Database locked
- SQLite doesn't support high concurrency
- Consider switching to PostgreSQL for production



## License

MIT License

## Support

For issues or questions, please contact support or create an issue in the repository.
