import firebase_admin
from firebase_admin import credentials, firestore
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

_db_client = None

def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    global _db_client
    if _db_client is None:
        firebase_credentials_path = os.getenv("FIREBASE_CREDENTIALS_PATH")
        if not firebase_credentials_path:
            raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable not set.")
        
        if not os.path.exists(firebase_credentials_path):
            raise FileNotFoundError(f"Firebase credentials file not found at: {firebase_credentials_path}")

        cred = credentials.Certificate(firebase_credentials_path)
        firebase_admin.initialize_app(cred)
        _db_client = firestore.client()
    return _db_client

def get_db():
    """Returns the Firestore client, ensuring Firebase is initialized."""
    return initialize_firebase()

