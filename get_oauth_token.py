from google_auth_oauthlib.flow import InstalledAppFlow

def get_refresh_token():
    print("Opening browser for authentication...")
    # This scope allows sending email
    SCOPES = ['https://mail.google.com/']
    
    # You will need to replace these with your actual Client ID and Secret if not prompted
    client_config = {
        "installed": {
            "client_id": "YOUR_CLIENT_ID_HERE.apps.googleusercontent.com",
            "client_secret": "YOUR_CLIENT_SECRET_HERE",
            "redirect_uris": ["http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token"
        }
    }
    
    # Ask user for credentials
    print("\n--- Google OAuth2 Setup ---")
    print("1. Create a Project in Google Cloud Console.")
    print("2. Enable the 'Gmail API'.")
    print("3. Create 'OAuth client ID' credentials type 'Desktop app'.")
    
    client_id = input("\nEnter your Client ID: ").strip()
    client_secret = input("Enter your Client Secret: ").strip()
    
    client_config['installed']['client_id'] = client_id
    client_config['installed']['client_secret'] = client_secret

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0)
    
    print("\nSUCCESS! Here are your credentials for .env:")
    print(f"GMAIL_CLIENT_ID={client_id}")
    print(f"GMAIL_CLIENT_SECRET={client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("\nCopy these 3 lines into your d:\\NetApp\\.env file.")

if __name__ == '__main__':
    get_refresh_token()
