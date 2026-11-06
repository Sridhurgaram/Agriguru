import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class Config:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Environment & Security
    SECRET_KEY = os.getenv("SECRET_KEY", "agriguru-prod-secure-key-2026")
    FLASK_DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(BASE_DIR, "agriguru.db"))
    
    # API Credentials (never exposed to frontend)
    TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY", "")
    TWO_FACTOR_API_KEY = os.getenv("TWO_FACTOR_API_KEY", "7be799a1-5e26-11f0-a562-0200cd936042")
    
    # Cache Configuration
    CACHE_DIR = os.path.join(BASE_DIR, "cache")
    WEATHER_CACHE_TTL_SECONDS = 1800  # 30 minutes for live forecasts
    HISTORICAL_CACHE_TTL_DAYS = 90    # 90 days for historical NASA POWER climate data
    
    # Datasets and Models
    DATA_FILES = {
        'crop_weather': os.path.join(BASE_DIR, "cleaned_crop_data.csv"),
        'crop_soil': os.path.join(BASE_DIR, "crop_soil_requirements_with_tamil.csv"),
        'district_soil': os.path.join(BASE_DIR, "tn_district_soil_data.csv"),
        'price_data': os.path.join(BASE_DIR, "tamilnadu_crop_prices_quintal.csv"),
        'growth_data': os.path.join(BASE_DIR, "crop_avg_growth_days_only.csv"),
        'model': os.path.join(BASE_DIR, "crop_model.pkl"),
        'encoders': os.path.join(BASE_DIR, "encoders.pkl"),
        'evaluation': os.path.join(BASE_DIR, "evaluation_results.json")
    }
    
    # Fallback Weather with clear label (used only if all APIs fail)
    FALLBACK_WEATHER = {
        'temperature (°C)': 28.5,
        'humidity (%)': 65.0,
        'rainfall (mm)': 55.0,
        'wind_speed (km/h)': 12.0,
        'precipitation_prob (%)': 20.0,
        'condition': 'Partly Cloudy',
        'source': 'Regional TN Climate Baseline (Fallback)',
        'is_fallback': True
    }
    
    # Model parameters for LightGBM
    MODEL_PARAMS = {
        'num_leaves': 31,
        'learning_rate': 0.08,
        'n_estimators': 180,
        'random_state': 42,
        'verbose': -1
    }

os.makedirs(Config.CACHE_DIR, exist_ok=True)
