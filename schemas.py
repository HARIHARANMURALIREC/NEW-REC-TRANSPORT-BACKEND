from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List
from enum import Enum

# Enums
class UserRole(str, Enum):
    admin = "admin"
    driver = "driver"
    passenger = "passenger"

class RideStatus(str, Enum):
    requested = "requested"
    assigned = "assigned"
    accepted = "accepted"
    picking_up = "picking_up"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"

class RideAssignment(BaseModel):
    ride_id: str
    driver_id: str

class RideStart(BaseModel):
    ride_id: str
    start_km: int

class RideComplete(BaseModel):
    ride_id: str
    end_km: int
    actual_duration: Optional[int] = None  # in minutes

class LeaveStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"

# Base Schemas
class UserBase(BaseModel):
    name: str
    email: EmailStr
    phone: str
    role: UserRole

class UserCreate(UserBase):
    password: str

class UserCreateAdmin(BaseModel):
    name: str
    email: EmailStr
    phone: str
    role: UserRole

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class User(UserBase):
    id: str
    avatar: Optional[str] = None
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True

# Driver Schemas
class DriverBase(BaseModel):
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    license_plate: str
    vehicle_color: str
    license_number: str
    license_expiry: datetime

class DriverCreate(DriverBase):
    user: UserCreate

class DriverCreateAdmin(BaseModel):
    user: UserCreateAdmin
    vehicle_make: str
    vehicle_model: str
    vehicle_year: str
    license_plate: str
    vehicle_color: str
    license_number: str
    license_expiry: str

class Driver(DriverBase):
    id: str
    user_id: str
    rating: float
    total_rides: int
    is_online: bool
    current_km_reading: int
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    last_status_change: datetime
    user: User

    class Config:
        from_attributes = True

# Passenger Schemas
class PassengerBase(BaseModel):
    pass

class PassengerCreate(PassengerBase):
    user: UserCreate

class PassengerCreateAdmin(BaseModel):
    user: UserCreateAdmin

class Passenger(PassengerBase):
    id: str
    user_id: str
    rating: float
    total_rides: int
    user: User

    class Config:
        from_attributes = True

# Admin Schemas
class AdminBase(BaseModel):
    permissions: str

class AdminCreate(AdminBase):
    user: UserCreate

class Admin(AdminBase):
    id: str
    user_id: str
    user: User

    class Config:
        from_attributes = True

# Ride Schemas
class LocationBase(BaseModel):
    latitude: float
    longitude: float
    address: str

class RideBase(BaseModel):
    pickup_location: LocationBase
    dropoff_location: LocationBase

class RideCreate(RideBase):
    passenger_id: str

class Ride(BaseModel):
    id: str
    passenger_id: str
    driver_id: Optional[str] = None
    status: RideStatus
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: str
    requested_at: datetime
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    distance: float
    estimated_duration: int
    actual_duration: Optional[int] = None

    class Config:
        from_attributes = True

# Kilometer Entry Schemas
class KilometerEntryBase(BaseModel):
    start_km: int
    ride_id: Optional[str] = None

class KilometerEntryCreate(KilometerEntryBase):
    driver_id: str

class KilometerEntryComplete(BaseModel):
    end_km: int

class KilometerEntry(KilometerEntryBase):
    id: str
    driver_id: str
    end_km: Optional[int] = None
    date: datetime
    status: str

    class Config:
        from_attributes = True

# Fuel Entry Schemas
class FuelEntryBase(BaseModel):
    amount: float
    cost: float
    location: str

class FuelEntryCreate(FuelEntryBase):
    driver_id: str

class FuelEntry(FuelEntryBase):
    id: str
    driver_id: str
    date: datetime
    added_by: str
    admin_id: Optional[str] = None

    class Config:
        from_attributes = True

# Leave Request Schemas
class LeaveRequestBase(BaseModel):
    start_date: datetime
    end_date: datetime
    reason: str

class LeaveRequestCreate(LeaveRequestBase):
    driver_id: Optional[str] = None

class LeaveRequestReview(BaseModel):
    status: LeaveStatus
    comments: Optional[str] = None

class LeaveRequest(LeaveRequestBase):
    id: str
    driver_id: str
    status: LeaveStatus
    requested_at: datetime
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    comments: Optional[str] = None

    class Config:
        from_attributes = True

# Response Schemas
class Token(BaseModel):
    access_token: str
    token_type: str
    user: User

class DriverStatus(BaseModel):
    is_online: bool
    last_status_change: datetime
    current_km_reading: int

class DriverAttendance(BaseModel):
    id: str
    driver_id: str
    date: datetime
    start_time: datetime
    end_time: Optional[datetime] = None
    total_hours: Optional[float] = None
    status: str
    driver: Optional[Driver] = None

    class Config:
        from_attributes = True

class DriverAttendanceCreate(BaseModel):
    driver_id: str
    start_time: datetime

class DriverAttendanceUpdate(BaseModel):
    end_time: datetime

class DashboardStats(BaseModel):
    total_drivers: int
    active_drivers: int
    total_rides: int
    pending_leave_requests: int
    total_fuel_expenses: float