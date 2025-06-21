import os
from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

    # OpenAI Configuration
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

    # Flask configuration
    DEBUG = os.getenv("FLASK_ENV", "production") == "development"
    PORT = int(os.getenv("PORT", 5000))

class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# Dictionary for Flask app factory pattern (if needed)
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig
}
