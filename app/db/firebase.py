import firebase_admin
from firebase_admin import credentials, firestore
import os
import json # Import json module
from dotenv import load_dotenv
from app.config import settings # Import settings

# Load environment variables from .env file
load_dotenv()

_db_client = None

def initialize_firebase():
    """Initializes Firebase Admin SDK if not already initialized."""
    global _db_client
    if _db_client is None:
        # Use settings from app.config
        firebase_credentials_json = settings.FIREBASE_CREDENTIALS_JSON
        firebase_credentials_path = settings.FIREBASE_CREDENTIALS_PATH
        firebase_project_id = settings.FIREBASE_PROJECT_ID

        if not firebase_project_id:
            raise ValueError("FIREBASE_PROJECT_ID environment variable not set.")

        cred = None
        if firebase_credentials_json:
            try:
                cred_dict = json.loads(firebase_credentials_json)
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError as e:
                raise ValueError(f"Error decoding FIREBASE_CREDENTIALS_JSON: {e}")
            except Exception as e:
                raise ValueError(f"Error creating Firebase credentials from JSON: {e}")
        elif firebase_credentials_path:
            if not os.path.exists(firebase_credentials_path):
                raise FileNotFoundError(f"Firebase credentials file not found at: {firebase_credentials_path}")
            cred = credentials.Certificate(firebase_credentials_path)
        else:
            raise ValueError("Neither FIREBASE_CREDENTIALS_JSON nor FIREBASE_CREDENTIALS_PATH is set.")

        # Initialize the default app
        if not firebase_admin._apps: # Check if any app is already initialized
            firebase_admin.initialize_app(cred, {'projectId': firebase_project_id})
        
        # Pass credentials and project to AsyncClient explicitly
        _db_client = firestore.AsyncClient(project=firebase_project_id, credentials=cred.get_credential())
    return _db_client

def get_db():
    """Returns the Firestore client, ensuring Firebase is initialized."""
    return initialize_firebase()