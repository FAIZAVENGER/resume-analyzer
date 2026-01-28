import os
from datetime import timedelta

class Config:
    """Application configuration"""
    
    # Flask
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///resume_analyzer.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    REPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
    
    # AI Engine
    AI_MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_models')
    NLP_MODEL = 'en_core_web_md'  # SpaCy model
    
    # Scoring weights
    SCORING_WEIGHTS = {
        'skills_match': 0.35,
        'experience_relevance': 0.25,
        'education_match': 0.15,
        'keyword_density': 0.10,
        'formatting_score': 0.05,
        'certifications': 0.05,
        'projects': 0.05
    }
    
    # Batch processing
    MAX_BATCH_SIZE = 20
    MAX_CONCURRENT_PROCESSES = 4
    
    # Cache
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Security
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    
    # Rate limiting
    RATELIMIT_ENABLED = True
    RATELIMIT_STORAGE_URL = CACHE_REDIS_URL
    RATELIMIT_STRATEGY = 'fixed-window'
    RATELIMIT_DEFAULT = '100 per hour'
    
    # Session
    PERMANENT_SESSION_LIFETIME = timedelta(hours=1)
    
    @staticmethod
    def init_app(app):
        # Create directories
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
        os.makedirs(Config.REPORTS_FOLDER, exist_ok=True)
        os.makedirs(Config.AI_MODEL_PATH, exist_ok=True)
        
        # Initialize NLP model
        from .nlp_processor import NLPProcessor
        NLPProcessor.initialize_model()

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False
    # Production-specific settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
