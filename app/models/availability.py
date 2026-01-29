from datetime import date, time
from typing import Optional
from sqlmodel import Field, SQLModel, Relationship

class AvailabilityBase(SQLModel):
    day_of_week: Optional[int] = Field(None, description="0=Monday, 6=Sunday")
    specific_date: Optional[date] = None
    start_time: time
    end_time: time
    is_recurring: bool = Field(default=True)

class Availability(AvailabilityBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    staff_id: int = Field(foreign_key="user.id")
    
    staff: "User" = Relationship(back_populates="availabilities")

class AvailabilityCreate(AvailabilityBase):
    staff_id: int

class AvailabilityRead(AvailabilityBase):
    id: int
    staff_id: int
