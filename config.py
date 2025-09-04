import os

class Config:
    SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "dev.json")
    PROPERTY_ID = os.getenv("GA_PROPERTY_ID", "dev")
    SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]