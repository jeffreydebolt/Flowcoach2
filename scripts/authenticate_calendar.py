"""
Authentication script for Google Calendar.

This script handles the OAuth 2.0 flow for Google Calendar API access.
"""

import os
import logging
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Google Calendar API scopes
SCOPES = ['https://www.googleapis.com/auth/calendar']

def authenticate_calendar():
    """Run the OAuth 2.0 flow for Google Calendar."""
    logger.info("Starting Google Calendar authentication...")
    
    # Create tokens directory if it doesn't exist
    tokens_dir = 'tokens'
    if not os.path.exists(tokens_dir):
        os.makedirs(tokens_dir)
    
    token_path = os.path.join(tokens_dir, 'default_token.json')
    credentials = None
    
    # Check if token file exists
    if os.path.exists(token_path):
        logger.info("Loading existing credentials from token file")
        try:
            credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            logger.error(f"Error loading credentials: {e}")
            credentials = None
    
    # If credentials are expired but have refresh token, refresh them
    if credentials and credentials.expired and credentials.refresh_token:
        logger.info("Refreshing expired credentials")
        try:
            credentials.refresh(Request())
        except Exception as e:
            logger.error(f"Error refreshing credentials: {e}")
            credentials = None
    
    # If no valid credentials, run the OAuth flow
    if not credentials or not credentials.valid:
        logger.info("No valid credentials found. Starting OAuth flow...")
        
        # Check for client secrets file
        client_secrets_file = os.environ.get('GOOGLE_CLIENT_SECRETS_FILE', 'client_secrets.json')
        if not os.path.exists(client_secrets_file):
            logger.error(f"Client secrets file not found: {client_secrets_file}")
            logger.error("Please download the client secrets file from Google Cloud Console")
            logger.error("and save it as 'client_secrets.json' in the project directory")
            logger.error("or set the GOOGLE_CLIENT_SECRETS_FILE environment variable")
            return False
        
        try:
            flow = InstalledAppFlow.from_client_secrets_file(client_secrets_file, SCOPES)
            credentials = flow.run_local_server(port=0)
            
            # Save the credentials for the next run
            with open(token_path, 'w') as token:
                token.write(credentials.to_json())
            
            logger.info(f"Credentials saved to {token_path}")
        except Exception as e:
            logger.error(f"Error during OAuth flow: {e}")
            return False
    
    logger.info("Authentication successful!")
    return True

if __name__ == "__main__":
    authenticate_calendar()
