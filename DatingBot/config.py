import os
from datetime import timedelta

class Config:
    # Bot Configuration
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "")
    
    # Database Configuration
    DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///anonymous_dating.db")
    
    # Flask Configuration
    SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "anonymous_dating_bot_secret_key")
    
    # App Configuration
    DEBUG = os.environ.get("DEBUG", "False").lower() == "true"
    PORT = int(os.environ.get("PORT", 5000))
    HOST = "0.0.0.0"
    
    # Owner Configuration (your Telegram ID)
    OWNER_TELEGRAM_ID = os.environ.get("OWNER_TELEGRAM_ID", "")
    
    # Premium Features
    FREE_GENDER_VIEWS = 5  # Number of free gender views before premium required
    PREMIUM_PRICE_USD = 2.00  # Monthly premium price
    
    # Owner user IDs (have unlimited access)
    OWNER_IDS = [
        5518634633,  # Owner ID 1
        1078099033   # Owner ID 2
    ]
    
    # Matching Configuration
    MAX_MATCH_RETRIES = 5
    MATCH_COOLDOWN_HOURS = 1  # How long to wait before allowing new match after ending one
    INACTIVE_MATCH_HOURS = 24  # How long before ending inactive matches
    RECENT_MATCH_DAYS = 7  # Don't rematch with users from last N days
    
    # Privacy & Safety
    MAX_BIO_LENGTH = 500
    MAX_INTERESTS_LENGTH = 200
    MAX_MESSAGE_LENGTH = 1000
    MIN_AGE = 18
    MAX_AGE = 99
    
    # Anonymous ID Configuration
    ANONYMOUS_ID_LENGTH = 8
    ANONYMOUS_ID_PREFIX = "User"
    
    # Rate Limiting
    MAX_MESSAGES_PER_MINUTE = 10
    MAX_REPORTS_PER_DAY = 5
    
    # Logging
    LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
