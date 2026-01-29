from enum import Enum
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

class UserRole(str, Enum):
    ADMIN = "admin"
    STAFF = "staff"
    CLIENT = "client"

class UserBase(SQLModel):
    email: str = Field(unique=True, index=True)
    full_name: Optional[str] = None
    role: UserRole = Field(default=UserRole.CLIENT)
    is_active: bool = Field(default=True)

class User(UserBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    hashed_password: str

    # Relationships
    appointments_as_client: List["Appointment"] = Relationship(
        back_populates="client", 
        sa_relationship_kwargs={"foreign_keys": "Appointment.client_id"}
    )
    appointments_as_staff: List["Appointment"] = Relationship(
        back_populates="staff", 
        sa_relationship_kwargs={"foreign_keys": "Appointment.staff_id"}
    )
    availabilities: List["Availability"] = Relationship(back_populates="staff")

class UserCreate(UserBase):
    password: str

class UserUpdate(UserBase):
    email: Optional[str] = None
    password: Optional[str] = None

class UserRead(UserBase):
    id: int

class Token(SQLModel):
    access_token: str
    token_type: str

class TokenData(SQLModel):
    email: Optional[str] = None
