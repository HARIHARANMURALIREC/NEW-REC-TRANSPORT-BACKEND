from beanie import Document, Indexed
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum
import uuid

# Enums
class UserRole(str, Enum):
    ADMIN = "admin"
    DRIVER = "driver"
    PASSENGER = "passenger"

class RideStatus(str, Enum):
    REQUESTED = "requested"
    ASSIGNED = "assigned"
    ACCEPTED = "accepted"
    PICKING_UP = "picking_up"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class LeaveRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

# Base Models
class User(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Indexed(str)
    email: str = Indexed(str, unique=True)
    phone: str = Indexed(str)
    role: UserRole
    password_hash: str
    avatar: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
    
    class Settings:
        name = "users"
        indexes = [
            "email",
            "role",
            "created_at",
            "is_active"
        ]

class Driver(Document):
    __tablename__ = "drivers"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Indexed(str, unique=True)
    vehicle_make: str = Indexed(str)
    vehicle_model: str = Indexed(str)
    vehicle_year: int = Indexed(int)
    license_plate: str = Indexed(str, unique=True)
    vehicle_color: str
    license_number: str = Indexed(str, unique=True)
    license_expiry: datetime = Indexed(datetime)
    rating: float = Field(default=5.0)
    total_rides: int = Field(default=0)
    is_online: bool = Field(default=False)
    current_km_reading: int = Field(default=0)
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    last_status_change: datetime = Field(default_factory=datetime.utcnow)
    user: Optional[User] = None
    
    class Settings:
        name = "drivers"
        indexes = [
            "user_id",
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
            "license_plate",
            "license_number",
            "license_expiry",
            "rating",
            "total_rides",
            "is_online",
            "current_latitude",
            "current_longitude",
            "last_status_change"
        ]
    
    @classmethod
    async def create_driver(cls, **data):
        """Create driver with proper datetime handling"""
        if isinstance(data.get('license_expiry'), str):
            data['license_expiry'] = datetime.fromisoformat(data['license_expiry'].replace('Z', '+00:00'))
        return await cls(**data).insert()

class Passenger(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Indexed(str, unique=True)
    rating: float = Field(default=5.0)
    total_rides: int = Field(default=0)
    
    class Settings:
        name = "passengers"
        indexes = [
            "user_id",
            "rating",
            "total_rides"
        ]

class Admin(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Indexed(str, unique=True)
    permissions: str  # JSON string of permissions
    
    class Settings:
        name = "admins"
        indexes = [
            "user_id"
        ]

class Ride(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    passenger_id: str
    driver_id: Optional[str] = None
    status: RideStatus
    pickup_latitude: float
    pickup_longitude: float
    pickup_address: str
    dropoff_latitude: float
    dropoff_longitude: float
    dropoff_address: str
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_at: Optional[datetime] = None
    accepted_at: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    distance: float = Field(default=0.0)
    estimated_duration: int = Field(default=0)
    actual_duration: Optional[int] = None
    start_km: Optional[int] = None
    end_km: Optional[int] = None
    
    class Settings:
        name = "rides"
        indexes = [
            "passenger_id",
            "driver_id",
            "status",
            "requested_at",
            "assigned_at",
            "accepted_at",
            "picked_up_at",
            "completed_at",
            "cancelled_at",
            "distance"
        ]

class KilometerEntry(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    driver_id: str = Indexed(str)
    ride_id: Optional[str] = Indexed(str)
    start_km: int
    end_km: Optional[int] = None
    date: datetime = Field(default_factory=datetime.utcnow)
    is_completed: bool = Field(default=False)
    completed_at: Optional[datetime] = None
    
    class Settings:
        name = "kilometer_entries"
        indexes = [
            "driver_id",
            "ride_id",
            "date",
            "is_completed"
        ]

class FuelEntry(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    driver_id: str = Indexed(str)
    amount: float  # liters
    cost: float
    date: datetime = Field(default_factory=datetime.utcnow)
    location: str
    added_by: str  # driver, admin
    admin_id: Optional[str] = None
    
    class Settings:
        name = "fuel_entries"
        indexes = [
            "driver_id",
            "date",
            "added_by"
        ]

class LeaveRequest(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    driver_id: str = Indexed(str)
    start_date: datetime
    end_date: datetime
    reason: str
    status: LeaveRequestStatus = Field(default=LeaveRequestStatus.PENDING)
    requested_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewed_by: Optional[str] = None
    comments: Optional[str] = None
    
    class Settings:
        name = "leave_requests"
        indexes = [
            "driver_id",
            "status",
            "start_date",
            "end_date",
            "requested_at"
        ]

class DriverAttendance(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    driver_id: str = Indexed(str)
    date: datetime = Indexed(datetime)
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    total_hours: Optional[float] = None
    status: str = Field(default="present")  # present, absent, late
    
    class Settings:
        name = "driver_attendance"
        indexes = [
            "driver_id",
            "date",
            "status"
        ]

class Vehicle(Document):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    license_plate: str
    vehicle_color: str
    license_number: str
    license_expiry: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "vehicles"
        indexes = [
            "vehicle_make",
            "vehicle_model",
            "vehicle_year",
            "license_plate",
            "license_number",
            "license_expiry",
            "created_at",
            "updated_at"
        ]

# Pydantic models for API responses
class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: str
    role: UserRole
    avatar: Optional[str] = None
    created_at: datetime
    is_active: bool

class DriverResponse(BaseModel):
    id: str
    user_id: str
    vehicle_make: str
    vehicle_model: str
    vehicle_year: int
    license_plate: str
    vehicle_color: str
    license_number: str
    license_expiry: datetime
    rating: float
    total_rides: int
    is_online: bool
    current_km_reading: int
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    last_status_change: datetime
    user: Optional[UserResponse] = None

class PassengerResponse(BaseModel):
    id: str
    user_id: str
    rating: float
    total_rides: int
    user: Optional[UserResponse] = None

class RideResponse(BaseModel):
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
    passenger: Optional[PassengerResponse] = None
    driver: Optional[DriverResponse] = None 
