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
        cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        firebase_project_id = os.getenv("FIREBASE_PROJECT_ID") # Get project ID

        if not cred_dict:
            raise ValueError("FIREBASE_CREDENTIALS_PATH environment variable not set.")
        if not firebase_project_id:
            raise ValueError("FIREBASE_PROJECT_ID environment variable not set.")
        
        # if not os.path.exists(firebase_credentials_path):
        #     raise FileNotFoundError(f"Firebase credentials file not found at: {firebase_credentials_path}")

        cred = credentials.Certificate(cred_dict)
        
        # Initialize the default app
        # It's good practice to initialize the app once, and then get the client from it.
        # However, the firestore.AsyncClient can also be initialized directly with credentials.
        # Let's ensure the app is initialized with projectId.
        if not firebase_admin._apps: # Check if any app is already initialized
            firebase_admin.initialize_app(cred, {'projectId': firebase_project_id})
        
        # Pass credentials and project to AsyncClient explicitly
        # This is the most robust way to ensure the client uses the specified credentials.
        _db_client = firestore.AsyncClient(project=firebase_project_id, credentials=cred.get_credential())
    return _db_client

def get_db():
    """Returns the Firestore client, ensuring Firebase is initialized."""
    return initialize_firebase()
