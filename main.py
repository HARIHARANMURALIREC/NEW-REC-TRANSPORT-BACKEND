from fastapi import FastAPI, Depends, HTTPException, status, Security
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, date as dt_date
from typing import Optional, List
import uuid
import json

from database import init_database, create_default_users, close_database
from models import User, Driver, Passenger, Admin, Ride, KilometerEntry, FuelEntry, LeaveRequest, DriverAttendance, RideStatus, LeaveRequestStatus, Vehicle
from config import settings
from auth import get_password_hash, verify_password, create_access_token, get_current_user, get_current_admin, get_current_driver

# Create FastAPI app
app = FastAPI(title="RideShare API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    await init_database()
    await create_default_users()
    print("✅ MongoDB Atlas connected and ready!")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    await close_database()

# Test endpoint
@app.get("/test")
async def test_endpoint():
    return {"message": "Backend is working with MongoDB Atlas!", "status": "success"}

# Authentication endpoints
@app.post("/auth/login")
async def login(user_credentials: dict):
    print(f"🔐 Login attempt for email: {user_credentials.get('email')}")
    
    user = await User.find_one({"email": user_credentials.get("email")})
    
    if not user:
        print(f"❌ User not found for email: {user_credentials.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ User found: {user.name} (role: {user.role})")
    
    if not verify_password(user_credentials.get("password"), user.password_hash):
        print(f"❌ Password verification failed for user: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    print(f"✅ Password verified successfully for user: {user.email}")
    
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    print(f"🎉 Login successful for user: {user.name}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return current_user

# User management endpoints (admin only)
@app.post("/users")
async def create_user(user_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new user (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": user_data.get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create new user
    new_user = User(
        name=user_data.get("name"),
        email=user_data.get("email"),
        phone=user_data.get("phone"),
        role=user_data.get("role"),
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    return new_user

@app.post("/drivers")
async def create_driver(driver_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new driver (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": driver_data.get("user", {}).get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user first
    new_user = User(
        name=driver_data.get("user", {}).get("name"),
        email=driver_data.get("user", {}).get("email"),
        phone=driver_data.get("user", {}).get("phone"),
        role="driver",
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    # Create driver profile (without vehicle info)
    driver_profile = await Driver.create_driver(
        user_id=new_user.id,
        license_number=driver_data.get("license_number"),
        license_expiry=driver_data.get("license_expiry"),
        rating=driver_data.get("rating", 5.0),
        total_rides=driver_data.get("total_rides", 0),
        current_km_reading=driver_data.get("current_km_reading", 0)
    )
    
    return driver_profile

@app.post("/passengers")
async def create_passenger(passenger_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new passenger (admin only)"""
    # Check if user with this email already exists
    existing_user = await User.find_one({"email": passenger_data.get("user", {}).get("email")})
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Create user first
    new_user = User(
        name=passenger_data.get("user", {}).get("name"),
        email=passenger_data.get("user", {}).get("email"),
        phone=passenger_data.get("user", {}).get("phone"),
        role="passenger",
        password_hash=get_password_hash("password"),  # Default password
    )
    await new_user.insert()
    
    # Create passenger profile
    passenger_profile = Passenger(
        user_id=new_user.id,
        rating=passenger_data.get("rating", 5.0),
        total_rides=passenger_data.get("total_rides", 0)
    )
    await passenger_profile.insert()
    
    return passenger_profile

# Get all drivers
@app.get("/drivers")
async def get_all_drivers(current_user: User = Depends(get_current_admin)):
    """Get all drivers (admin only)"""
    drivers = await Driver.find_all().to_list()
    # Populate user info for each driver robustly
    user_ids = [str(driver.user_id) for driver in drivers]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    for driver in drivers:
        driver.user = users.get(str(driver.user_id))
    return drivers



# Get all passengers
@app.get("/passengers")
async def get_all_passengers(current_user: User = Depends(get_current_admin)):
    """Get all passengers (admin only)"""
    passengers = await Passenger.find_all().to_list()
    user_ids = [p.user_id for p in passengers]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    response = []
    for p in passengers:
        user = users.get(str(p.user_id))
        passenger_dict = p.dict()
        passenger_dict["user"] = user.dict() if user else None
        response.append(passenger_dict)
    return response

@app.post("/vehicles")
async def create_vehicle(vehicle_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a new vehicle (admin only, not attached to a driver)"""
    print(f"🚗 Creating vehicle with data: {vehicle_data}")
    
    # Validate required fields
    required_fields = [
        "vehicle_make", "vehicle_model", "vehicle_year", "license_plate",
        "vehicle_color", "license_number", "license_expiry"
    ]
    for field in required_fields:
        if not vehicle_data.get(field):
            print(f"❌ Missing required field: {field}")
            raise HTTPException(status_code=400, detail=f"Missing required field: {field}")
    
    # Parse license_expiry to datetime
    license_expiry = vehicle_data["license_expiry"]
    if isinstance(license_expiry, str):
        try:
            license_expiry = datetime.strptime(license_expiry, "%d-%m-%Y")
            print(f"✅ Parsed license_expiry: {license_expiry}")
        except Exception as e:
            print(f"❌ Error parsing license_expiry: {e}")
            raise HTTPException(status_code=400, detail="license_expiry must be in DD-MM-YYYY format")
    
    try:
        vehicle = Vehicle(
            vehicle_make=vehicle_data["vehicle_make"],
            vehicle_model=vehicle_data["vehicle_model"],
            vehicle_year=int(vehicle_data["vehicle_year"]),
            license_plate=vehicle_data["license_plate"],
            vehicle_color=vehicle_data["vehicle_color"],
            license_number=vehicle_data["license_number"],
            license_expiry=license_expiry
        )
        await vehicle.insert()
        print(f"✅ Vehicle created successfully with ID: {vehicle.id}")
        return vehicle
    except Exception as e:
        print(f"❌ Error creating vehicle: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create vehicle: {str(e)}")

@app.get("/vehicles")
async def get_all_vehicles(current_user: User = Depends(get_current_admin)):
    """Get all vehicles (admin only) - includes both direct vehicles and driver vehicles"""
    # Vehicles created directly
    vehicles = await Vehicle.find_all().to_list()
    vehicle_list = [
        {
            "id": v.id,
            "vehicle_make": v.vehicle_make,
            "vehicle_model": v.vehicle_model,
            "vehicle_year": v.vehicle_year,
            "license_plate": v.license_plate,
            "vehicle_color": v.vehicle_color,
            "license_number": v.license_number,
            "license_expiry": v.license_expiry.isoformat() if v.license_expiry else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
            "updated_at": v.updated_at.isoformat() if v.updated_at else None
        }
        for v in vehicles
    ]
    # Vehicles attached to drivers
    drivers = await Driver.find_all().to_list()
    for driver in drivers:
        if (driver.vehicle_make and driver.vehicle_model and 
            driver.license_plate and driver.vehicle_color):
            vehicle_list.append({
                "id": str(driver.id),
                "vehicle_make": driver.vehicle_make,
                "vehicle_model": driver.vehicle_model,
                "vehicle_year": driver.vehicle_year,
                "license_plate": driver.license_plate,
                "vehicle_color": driver.vehicle_color,
                "license_number": driver.license_number,
                "license_expiry": driver.license_expiry.isoformat() if driver.license_expiry else None,
                "created_at": driver.created_at.isoformat() if hasattr(driver, 'created_at') and driver.created_at else None,
                "updated_at": driver.updated_at.isoformat() if hasattr(driver, 'updated_at') and driver.updated_at else None
            })
    return vehicle_list

# Ride management
@app.post("/rides")
async def create_ride(ride_data: dict):
    """Create a new ride"""
    new_ride = Ride(
        passenger_id=ride_data.get("passenger_id"),
        pickup_latitude=ride_data.get("pickup_latitude"),
        pickup_longitude=ride_data.get("pickup_longitude"),
        pickup_address=ride_data.get("pickup_address"),
        dropoff_latitude=ride_data.get("dropoff_latitude"),
        dropoff_longitude=ride_data.get("dropoff_longitude"),
        dropoff_address=ride_data.get("dropoff_address"),
        status=RideStatus.REQUESTED
    )
    await new_ride.insert()
    return new_ride

@app.get("/rides")
async def get_rides(passenger_id: Optional[str] = None, driver_id: Optional[str] = None):
    """Get rides with optional filters and populate driver and passenger info"""
    query = {}
    if passenger_id:
        query["passenger_id"] = passenger_id
    if driver_id:
        query["driver_id"] = driver_id

    rides = await Ride.find(query).to_list()

    # Collect all driver and passenger IDs
    driver_ids = [ride.driver_id for ride in rides if ride.driver_id]
    passenger_ids = [ride.passenger_id for ride in rides if ride.passenger_id]

    # Fetch drivers and passengers
    drivers = {d.id: d async for d in Driver.find({"id": {"$in": driver_ids}})}
    passengers = {p.id: p async for p in Passenger.find({"id": {"$in": passenger_ids}})}

    # Fetch all user IDs
    user_ids = [d.user_id for d in drivers.values()] + [p.user_id for p in passengers.values()]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}

    # Attach driver and passenger user info to each ride
    for ride in rides:
        driver = drivers.get(ride.driver_id)
        if driver:
            driver.user = users.get(str(driver.user_id))
            ride.driver = driver
        passenger = passengers.get(ride.passenger_id)
        if passenger:
            passenger.user = users.get(str(passenger.user_id))
            ride.passenger = passenger

    return rides

@app.get("/rides/pending")
async def get_pending_rides(current_user: User = Depends(get_current_admin)):
    """Get all pending rides (admin only)"""
    rides = await Ride.find({"status": RideStatus.REQUESTED}).to_list()
    return rides

@app.get("/rides/assigned")
async def get_assigned_rides(current_user: User = Depends(get_current_driver)):
    """Get rides assigned to current driver"""
    rides = await Ride.find({"driver_id": current_user.id, "status": {"$in": [RideStatus.ASSIGNED, RideStatus.IN_PROGRESS]}}).to_list()
    
    # Collect all passenger IDs
    passenger_ids = [ride.passenger_id for ride in rides if ride.passenger_id]
    
    # Fetch passengers
    passengers = {p.id: p async for p in Passenger.find({"id": {"$in": passenger_ids}})}
    
    # Fetch all user IDs for passengers
    user_ids = [p.user_id for p in passengers.values()]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    
    # Attach passenger user info to each ride
    for ride in rides:
        passenger = passengers.get(ride.passenger_id)
        if passenger:
            passenger.user = users.get(str(passenger.user_id))
            ride.passenger = passenger
    
    return rides

@app.post("/rides/{ride_id}/assign")
async def assign_ride(ride_id: str, assignment_data: dict, current_user: User = Depends(get_current_admin)):
    """Assign a ride to a driver (admin only)"""
    ride = await Ride.find_one({"_id": ride_id})
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    if ride.status != RideStatus.REQUESTED:
        raise HTTPException(status_code=400, detail="Ride is not in pending status")
    
    driver_id = assignment_data.get("driver_id")
    driver = await Driver.find_one({"_id": driver_id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    ride.driver_id = driver_id
    ride.status = RideStatus.ASSIGNED
    ride.assigned_at = datetime.utcnow()
    await ride.save()
    
    return {"message": "Ride assigned successfully", "ride": ride}

@app.post("/rides/manual")
async def create_manual_ride(ride_data: dict, current_user: User = Depends(get_current_admin)):
    """Create a ride and assign it to a driver (admin only)"""
    # Create the ride
    new_ride = Ride(
        passenger_id=ride_data.get("passenger_id"),
        driver_id=ride_data.get("driver_id"),
        pickup_latitude=ride_data.get("pickup_latitude"),
        pickup_longitude=ride_data.get("pickup_longitude"),
        pickup_address=ride_data.get("pickup_address"),
        dropoff_latitude=ride_data.get("dropoff_latitude"),
        dropoff_longitude=ride_data.get("dropoff_longitude"),
        dropoff_address=ride_data.get("dropoff_address"),
        status=RideStatus.ASSIGNED,
        assigned_at=datetime.utcnow()
    )
    await new_ride.insert()
    return new_ride

@app.post("/rides/{ride_id}/start")
async def start_ride(ride_id: str, start_data: dict, current_user: User = Depends(get_current_driver)):
    """Start a ride (driver only)"""
    ride = await Ride.find_one({"_id": ride_id, "driver_id": current_user.id})
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    if ride.status != RideStatus.ASSIGNED:
        raise HTTPException(status_code=400, detail="Ride is not assigned")
    
    ride.status = RideStatus.IN_PROGRESS
    ride.picked_up_at = datetime.utcnow()
    ride.start_km = start_data.get("start_km")
    await ride.save()
    
    return {"message": "Ride started successfully", "ride": ride}

@app.post("/rides/{ride_id}/complete")
async def complete_ride(ride_id: str, complete_data: dict, current_user: User = Depends(get_current_driver)):
    """Complete a ride (driver only)"""
    ride = await Ride.find_one({"_id": ride_id, "driver_id": current_user.id})
    if not ride:
        raise HTTPException(status_code=404, detail="Ride not found")
    
    if ride.status != RideStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="Ride is not in progress")
    
    end_km = complete_data.get("end_km")
    distance = end_km - ride.start_km if ride.start_km and end_km else 0
    
    ride.status = RideStatus.COMPLETED
    ride.completed_at = datetime.utcnow()
    ride.end_km = end_km
    ride.distance = distance
    await ride.save()
    
    return {"message": "Ride completed successfully", "ride": ride, "distance": distance}

# Driver status update
@app.put("/drivers/me/status")
async def update_my_status(is_online: bool, current_user: User = Depends(get_current_driver)):
    """Update driver's online status and attendance"""
    driver = await Driver.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")

    now = datetime.utcnow()
    driver.is_online = is_online
    driver.last_status_change = now
    await driver.save()

    # Attendance logic
    today = dt_date.today()
    attendance = await DriverAttendance.find_one({
        "driver_id": driver.id,  # FIX: use driver.id, not current_user.id
        "date": datetime(today.year, today.month, today.day)
    })

    if is_online:
        # If going online and no attendance for today, create it
        if not attendance:
            attendance = DriverAttendance(
                driver_id=driver.id,  # FIX: use driver.id
                date=datetime(today.year, today.month, today.day),
                check_in=now,
                status="present"
            )
            await attendance.insert()
        else:
            # If already present, but no check_in, update it
            if not attendance.check_in:
                attendance.check_in = now
                attendance.status = "present"
                await attendance.save()
    else:
        # If going offline, update check_out and total_hours
        if attendance and not attendance.check_out:
            attendance.check_out = now
            if attendance.check_in:
                attendance.total_hours = (attendance.check_out - attendance.check_in).total_seconds() / 3600.0
            else:
                attendance.total_hours = 0.0
            await attendance.save()

    return {"message": f"Driver status updated to {'online' if is_online else 'offline'}"}

@app.post("/leave-requests")
async def create_leave_request(leave_data: dict, current_user: User = Depends(get_current_driver)):
    """Create a new leave request (driver only)"""
    new_leave = LeaveRequest(
        driver_id=current_user.id,
        start_date=leave_data.get("start_date"),
        end_date=leave_data.get("end_date"),
        reason=leave_data.get("reason"),
        status=LeaveRequestStatus.PENDING,
        requested_at=datetime.utcnow()
    )
    await new_leave.insert()
    return new_leave

@app.post("/fuel-entries")
async def create_fuel_entry(fuel_data: dict, current_user: User = Depends(get_current_driver)):
    new_entry = FuelEntry(
        driver_id=current_user.id,
        amount=fuel_data.get("amount"),
        cost=fuel_data.get("cost"),
        date=datetime.utcnow(),
        location=fuel_data.get("location"),
        added_by="driver"
    )
    await new_entry.insert()
    print("[DEBUG] Inserted fuel entry:", new_entry.dict())
    return new_entry

@app.get("/fuel-entries")
async def get_fuel_entries(
    driver_id: Optional[str] = None,
    current_user: User = Security(get_current_user)
):
    # If admin, allow any query and enrich
    if current_user.role == "admin":
        query = {}
        if driver_id:
            query["driver_id"] = driver_id
        entries = await FuelEntry.find(query).to_list()
        print(f"[DEBUG] Admin fetched fuel entries: {[e.dict() for e in entries]}")
        # Enrich with driver and user info
        driver_user_ids = list(set([e.driver_id for e in entries]))
        drivers = await Driver.find({"user_id": {"$in": driver_user_ids}}).to_list()
        driver_dict = {str(d.user_id): d for d in drivers}
        user_ids = [d.user_id for d in drivers]
        users = await User.find({"_id": {"$in": user_ids}}).to_list()
        user_dict = {str(u.id): u for u in users}
        response = []
        for entry in entries:
            driver = driver_dict.get(str(entry.driver_id))
            user = user_dict.get(str(entry.driver_id)) if driver else None
            response.append({
                "id": entry.id,
                "driver_id": entry.driver_id,
                "amount": entry.amount,
                "cost": entry.cost,
                "date": entry.date.isoformat() if entry.date else None,
                "location": entry.location,
                "added_by": entry.added_by,
                "admin_id": entry.admin_id,
                "driver": {
                    "id": driver.id if driver else None,
                    "user_id": driver.user_id if driver else None,
                    "vehicle_make": driver.vehicle_make if driver else None,
                    "vehicle_model": driver.vehicle_model if driver else None,
                    "vehicle_year": driver.vehicle_year if driver else None,
                    "license_plate": driver.license_plate if driver else None,
                    "name": user.name if user else None,
                    "user": {"id": user.id, "name": user.name, "email": user.email} if user else None
                } if driver and user else None
            })
        return response
    # If driver, only allow their own entries
    elif current_user.role == "driver":
        entries = await FuelEntry.find({"driver_id": current_user.id}).to_list()
        print(f"[DEBUG] Driver {current_user.id} fetched fuel entries: {[e.dict() for e in entries]}")
        return [
            {
                "id": entry.id,
                "driver_id": entry.driver_id,
                "amount": entry.amount,
                "cost": entry.cost,
                "date": entry.date.isoformat() if entry.date else None,
                "location": entry.location,
                "added_by": entry.added_by,
                "admin_id": entry.admin_id
            }
            for entry in entries
        ]
    else:
        raise HTTPException(status_code=403, detail="Not authorized")

# Add this endpoint to support attendance fetching for admin
@app.get("/attendance")
async def get_attendance(driver_id: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, current_user: User = Depends(get_current_admin)):
    """Get driver attendance records (admin only)"""
    query = {}
    if driver_id:
        query["driver_id"] = driver_id
    if start_date:
        from datetime import datetime
        query["date"] = {"$gte": datetime.fromisoformat(start_date)}
    if end_date:
        from datetime import datetime
        if "date" in query:
            query["date"]["$lte"] = datetime.fromisoformat(end_date)
        else:
            query["date"] = {"$lte": datetime.fromisoformat(end_date)}
    records = await DriverAttendance.find(query).to_list()
    # Populate driver info
    driver_ids = list(set([str(r.driver_id) for r in records]))
    drivers = {str(d.id): d async for d in Driver.find({"id": {"$in": driver_ids}})}
    user_ids = [d.user_id for d in drivers.values()]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    response = []
    # Explicitly fetch all drivers
    drivers = await Driver.find_all().to_list()
    # Build user_ids from the new drivers list
    user_ids = [d.user_id for d in drivers]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    # Build driver and user lookup dicts with string keys
    driver_dict = {str(d.id): d for d in drivers}
    user_dict = {str(u.id): u for u in users.values()} if isinstance(users, dict) else {str(u.id): u for u in users}
    print(f"[DEBUG] All driver_dict keys: {list(driver_dict.keys())}")
    print(f"[DEBUG] All attendance driver_ids: {[str(r.driver_id) for r in records]}")
    for record in records:
        lookup_id = str(record.driver_id)
        driver = driver_dict.get(lookup_id)
        print(f"[DEBUG] Looking up driver_id={lookup_id}: {'FOUND' if driver else 'NOT FOUND'}")
        user = user_dict.get(str(driver.user_id)) if driver else None
        if driver and user:
            print(f"[DEBUG] Found driver {driver.id} for attendance, user: {user.name}")
        response.append({
            "id": getattr(record, 'id', getattr(record, '_id', None)),
            "driver_id": record.driver_id,
            "date": record.date.isoformat() if record.date else None,
            "check_in": record.check_in.isoformat() if record.check_in else None,
            "check_out": record.check_out.isoformat() if record.check_out else None,
            "total_hours": record.total_hours,
            "status": record.status,
            "driver": {
                "id": getattr(driver, 'id', None) if driver else None,
                "user_id": getattr(driver, 'user_id', None) if driver else None,
                "name": user.name if user else None,
                "user": {"id": user.id, "name": user.name, "email": user.email} if user else None
            } if driver else None
        })
    return response

@app.get("/debug/drivers-and-attendance")
async def debug_drivers_and_attendance(current_user: User = Depends(get_current_admin)):
    """Return all drivers and attendance records for debugging ID mismatches (admin only)"""
    drivers = await Driver.find_all().to_list()
    attendance = await DriverAttendance.find_all().to_list()
    return {
        "drivers": [
            {"id": d.id, "name": getattr(d, 'name', None) or getattr(d, 'user', None) and getattr(d.user, 'name', None), "user_id": d.user_id} for d in drivers
        ],
        "attendance": [
            {"id": a.id, "driver_id": a.driver_id, "date": a.date.isoformat() if a.date else None} for a in attendance
        ]
    }

@app.get("/debug/orphaned-attendance")
async def debug_orphaned_attendance(current_user: User = Depends(get_current_admin)):
    """Return all attendance records whose driver_id does not match any driver (admin only)"""
    drivers = await Driver.find_all().to_list()
    driver_ids = set(str(d.id) for d in drivers)
    attendance = await DriverAttendance.find_all().to_list()
    orphaned = [
        {"id": a.id, "driver_id": a.driver_id, "date": a.date.isoformat() if a.date else None}
        for a in attendance if str(a.driver_id) not in driver_ids
    ]
    return {"orphaned_attendance": orphaned, "total_orphaned": len(orphaned)}

@app.delete("/debug/delete-orphaned-attendance")
async def delete_orphaned_attendance(current_user: User = Depends(get_current_admin)):
    """Delete all attendance records whose driver_id does not match any driver (admin only)"""
    drivers = await Driver.find_all().to_list()
    driver_ids = set(str(d.id) for d in drivers)
    attendance = await DriverAttendance.find_all().to_list()
    orphaned = [a for a in attendance if str(a.driver_id) not in driver_ids]
    count = 0
    for a in orphaned:
        await a.delete()
        count += 1
    return {"deleted_orphaned_attendance": count}

@app.get("/debug/users")
async def debug_users(current_user: User = Depends(get_current_admin)):
    users = await User.find_all().to_list()
    return [{"id": u.id, "name": u.name, "email": u.email} for u in users]

@app.get("/debug/drivers-users")
async def debug_drivers_users(current_user: User = Depends(get_current_admin)):
    drivers = await Driver.find_all().to_list()
    user_ids = [str(driver.user_id) for driver in drivers]
    users = {str(u.id): u async for u in User.find({"_id": {"$in": user_ids}})}
    debug_list = []
    for driver in drivers:
        user = users.get(str(driver.user_id))
        debug_list.append({
            "driver_id": driver.id,
            "driver_user_id": driver.user_id,
            "user_id": user.id if user else None,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None
        })
    return debug_list

@app.get("/drivers/me")
async def get_my_driver_profile(current_user: User = Depends(get_current_driver)):
    """Get the current driver's profile (driver only)"""
    driver = await Driver.find_one({"user_id": current_user.id})
    if not driver:
        raise HTTPException(status_code=404, detail="Driver profile not found")
    # Populate user info
    driver.user = current_user
    return driver

# Health check
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "database": "MongoDB Atlas", "timestamp": datetime.utcnow()}
