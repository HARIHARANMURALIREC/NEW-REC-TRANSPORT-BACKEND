import os
import certifi
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models import User, Driver, Passenger, Admin, Ride, KilometerEntry, FuelEntry, LeaveRequest, DriverAttendance, Vehicle
from config import settings
import asyncio
import ssl

# MongoDB client
client: AsyncIOMotorClient = None

async def init_database():
    """Initialize MongoDB connection and Beanie ODM"""
    global client
    
    # Use environment variable for MongoDB connection string
    mongodb_url = os.environ.get("MONGODB_URL") or getattr(settings, 'MONGODB_URL', None)
    if not mongodb_url:
        raise RuntimeError("MONGODB_URL environment variable not set!")
    client = AsyncIOMotorClient(
        mongodb_url,
        tlsCAFile=certifi.where()
    )
    
    # Initialize Beanie with the document models
    await init_beanie(
        database=client["rideshare"],
        document_models=[
            User,
            Driver,
            Passenger,
            Admin,
            Ride,
            KilometerEntry,
            FuelEntry,
            LeaveRequest,
            DriverAttendance,
            Vehicle
        ]
    )
    print(f"✅ Connected to MongoDB Atlas: rideshare")

async def close_database():
    """Close MongoDB connection"""
    global client
    if client:
        client.close()
        print("✅ MongoDB connection closed")

async def create_default_users():
    """Create default users if they don't exist"""
    # Check if admin user exists
    admin_user = await User.find_one({"email": "admin@rideshare.com"})
    if not admin_user:
        print("Creating default users...")
        
        # Create admin user
        admin_user = User(
            name="Admin User",
            email="admin@rideshare.com",
            phone="+1234567890",
            role="admin",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KqjqKq"  # "password"
        )
        await admin_user.insert()
        
        # Create admin profile
        admin_profile = Admin(
            user_id=admin_user.id,
            permissions='["view_all", "manage_drivers", "manage_rides"]'
        )
        await admin_profile.insert()
        
        # Create sample driver
        driver_user = User(
            name="John Driver",
            email="driver@rideshare.com",
            phone="+1234567891",
            role="driver",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KqjqKq"  # "password"
        )
        await driver_user.insert()
        
        driver_profile = Driver(
            user_id=driver_user.id,
            vehicle_make="Toyota",
            vehicle_model="Camry",
            vehicle_year=2020,
            license_plate="ABC-123",
            vehicle_color="Silver",
            license_number="DL123456789",
            license_expiry="2025-12-31T00:00:00Z",
            rating=4.8,
            total_rides=1250,
            current_km_reading=45230
        )
        await driver_profile.insert()
        
        # Create sample passenger
        passenger_user = User(
            name="Jane Passenger",
            email="passenger@rideshare.com",
            phone="+1234567892",
            role="passenger",
            password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewdBPj4J/8KqjqKq"  # "password"
        )
        await passenger_user.insert()
        
        passenger_profile = Passenger(
            user_id=passenger_user.id,
            rating=4.9,
            total_rides=89
        )
        await passenger_profile.insert()
        
        print("✅ Default users created successfully")
    else:
        print("✅ Default users already exist")

# Database dependency for FastAPI
async def get_database():
    """Get database instance"""
    return client[settings.MONGODB_DATABASE]

# Health check
async def health_check():
    """Check database connectivity"""
    try:
        await client.admin.command('ping')
        return True
    except Exception as e:
        print(f"❌ Database health check failed: {e}")
        return False
