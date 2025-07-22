import os
from typing import List
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App settings
    APP_NAME: str = "RideShare API"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # MongoDB Atlas
    MONGODB_URL: str = os.environ.get("MONGODB_URL", "mongodb+srv://gpsapp:upB19T8wF8YoDYqj@cluster0.wzwmzbo.mongodb.net/rideshare?retryWrites=true&w=majority&appName=Cluster0")
    MONGODB_DATABASE: str = os.environ.get("MONGODB_DATABASE", "rideshare")
    MONGODB_MAX_POOL_SIZE: int = 100
    MONGODB_MIN_POOL_SIZE: int = 10
    MONGODB_MAX_IDLE_TIME_MS: int = 30000
    MONGODB_CONNECT_TIMEOUT_MS: int = 20000
    MONGODB_SERVER_SELECTION_TIMEOUT_MS: int = 5000
    
    # Redis (for caching and sessions)
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_PASSWORD: str = ""
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY: str = ""
    
    # Monitoring
    SENTRY_DSN: str = ""
    ENABLE_METRICS: bool = True
    
    # Background tasks
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    
    # File uploads
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_DIR: str = "uploads"
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"

# Create settings instance
settings = Settings()

# Environment-specific configurations
def get_mongodb_url():
    """Get MongoDB URL based on environment"""
    # Priority: Environment variable > Production default > Development default
    if os.getenv("MONGODB_URL"):
        return os.getenv("MONGODB_URL")
    elif os.getenv("ENVIRONMENT") == "production":
        # MongoDB Atlas connection string format for production:
        # mongodb+srv://username:password@cluster.mongodb.net/database?retryWrites=true&w=majority
        return os.getenv("MONGODB_URL", "mongodb+srv://username:password@cluster.mongodb.net/rideshare?retryWrites=true&w=majority")
    else:
        # For development, you can use MongoDB Atlas or local MongoDB
        return os.getenv("MONGODB_URL", "mongodb+srv://username:password@cluster.mongodb.net/rideshare?retryWrites=true&w=majority")

def get_redis_url():
    """Get Redis URL based on environment"""
    if os.getenv("REDIS_URL"):
        return os.getenv("REDIS_URL")
    elif os.getenv("ENVIRONMENT") == "production":
        return os.getenv("REDIS_URL", "redis://localhost:6379")
    else:
        return "redis://localhost:6379"

# Update settings with environment-specific values
settings.MONGODB_URL = get_mongodb_url()
settings.REDIS_URL = get_redis_url() 