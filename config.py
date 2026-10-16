import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "crisiscore-super-secret-production-key-2026")
    DATABASE_PATH = os.path.join(BASE_DIR, "crisiscore.db")
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024  # 32MB max upload
    ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "mp4", "mov"}
    
    # Official NDMA / SDMA Integration Configuration
    NDMA_API_ENDPOINT = "https://neoc.ndma.gov.in/api/v2/cap/dispatch"
    SDMA_API_ENDPOINT = "https://sdma-alert.gov.in/gateway/v1/incidents"
    ENABLE_LIVE_GOV_MOCK = True  # Transparent simulation of authorized gateway
