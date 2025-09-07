import os

class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret_key")
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "dev.json")
    CLIENT_SECRET = os.getenv("GA_CLIENT_SECRET", "dev.json")
    PROPERTY_ID = os.getenv("GA_PROPERTY_ID", "dev")
    SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
    REDIRECT_URI = "http://127.0.0.1:5000/oauth2callback"