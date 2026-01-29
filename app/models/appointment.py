from datetime import datetime
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class AppointmentStatus(str, Enum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"

class AppointmentBase(SQLModel):
    start_time: datetime
    end_time: datetime
    notes: Optional[str] = None
    status: AppointmentStatus = Field(default=AppointmentStatus.SCHEDULED)

class Appointment(AppointmentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="user.id")
    staff_id: int = Field(foreign_key="user.id")

    client: "User" = Relationship(
        back_populates="appointments_as_client",
        sa_relationship_kwargs={"foreign_keys": "Appointment.client_id"}
    )
    staff: "User" = Relationship(
        back_populates="appointments_as_staff",
        sa_relationship_kwargs={"foreign_keys": "Appointment.staff_id"}
    )

class AppointmentCreate(AppointmentBase):
    staff_id: int

class AppointmentUpdate(SQLModel):
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[AppointmentStatus] = None

class AppointmentReschedule(SQLModel):
    new_start_time: datetime
    new_end_time: datetime
    reason: Optional[str] = None

class AppointmentRead(AppointmentBase):
    id: int
    client_id: int
    staff_id: int
