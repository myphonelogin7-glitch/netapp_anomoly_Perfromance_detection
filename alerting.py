import os
import smtplib
import ssl
from email.message import EmailMessage
from dotenv import load_dotenv
import requests
import base64
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

load_dotenv()

# Fallback credentials (user-provided) – will be used if environment variables are not set
GMAIL_USER = os.getenv('GMAIL_USER', 'myphonelogin7@gmail.com')
GMAIL_APP_PASSWORD = os.getenv('GMAIL_APP_PASSWORD', 'P0w3rL0ck')

# OAuth2 Credentials
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_REFRESH_TOKEN = os.getenv('GMAIL_REFRESH_TOKEN')

# NOTE: Teams requires an incoming webhook URL, not an email address. Use a placeholder if not set.
TEAMS_WEBHOOK_URL = os.getenv('TEAMS_WEBHOOK_URL', 'https://outlook.office.com/webhook/PLACEHOLDER')


def format_email_body(anomaly_data):
    """
    Formats a plain-text email body for storage alerts.
    """
    return f"""
    Subject: CRITICAL: Standard Storage Anomaly Detected - {anomaly_data['Volume_Name']}
    
    To: Storage Admin Team
    From: NetApp AI Monitor (POC)
    
    ALERT DETAILS:
    --------------------------------------------------
    Severity:       {anomaly_data['Severity']}
    Volume:         {anomaly_data['Volume_Name']}
    Metric:         Latency
    Observed Value: {anomaly_data['Latency_ms']} ms
    Normal Range:   0 - {anomaly_data['Upper_Bound']:.2f} ms
    Timestamp:      {anomaly_data['Timestamp']}
    Root Cause:     {anomaly_data.get('Root_Cause', 'Unknown')}
    --------------------------------------------------
    
    Review the dashboard immediately for recommended resolution steps.
    """

def format_teams_card(data):
    """Formats a Microsoft Teams MessageCard.
    Works with both legacy `anomaly_data` and new AI investigation result dicts.
    """
    if 'Volume_Name' in data:
        return {
            "@type": "MessageCard",
            "summary": "Storage Anomaly Alert",
            "sections": [{
                "activityTitle": "Storage Performance Alert",
                "activitySubtitle": f"Volume: {data['Volume_Name']}",
                "facts": [
                    {"name": "Severity", "value": data['Severity']},
                    {"name": "Latency", "value": f"{data['Latency_ms']} ms"},
                    {"name": "Timestamp", "value": str(data['Timestamp'])},
                    {"name": "Analysis", "value": data.get('Root_Cause', 'N/A')}
                ],
                "text": "NetApp AI POC has detected unusual behavior. Please investigate."
            }]
        }
    else:
        findings = data.get('findings', {})
        analysis = data.get('analysis', {})
        return {
            "@type": "MessageCard",
            "summary": f"AI Alert: {findings.get('primary_cause', 'N/A')}",
            "sections": [{
                "activityTitle": "AI Performance Investigation",
                "activitySubtitle": f"Volume: {data.get('volume', 'N/A')} | Severity: {data.get('severity', 'N/A')}",
                "facts": [
                    {"name": "Cause", "value": findings.get('primary_cause', 'N/A')},
                    {"name": "Confidence", "value": findings.get('confidence_score', 'N/A')},
                    {"name": "Pattern", "value": analysis.get('behavior_pattern', 'N/A')},
                    {"name": "Action", "value": "See Attached PDF"}
                ],
                "text": analysis.get('description', '')
            }]
        }

# Duplicate import block removed – imports are already at the top of the file



def get_gmail_access_token():
    """Rerieve a valid access token using the refresh token."""
    if not all([GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN]):
        return None
    
    creds = Credentials(
        None,
        refresh_token=GMAIL_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=GMAIL_CLIENT_ID,
        client_secret=GMAIL_CLIENT_SECRET
    )
    
    try:
        creds.refresh(Request())
        return creds.token
    except Exception as e:
        print(f"[OAUTH ERROR] Failed to refresh token: {e}")
        return None

def send_email(investigation_result, attachment=None):
    """Send an email via Gmail using OAuth2 (preferred) or App Password.
    """
    user = GMAIL_USER
    
    # Try OAuth2 first
    access_token = get_gmail_access_token()
    use_oauth = bool(access_token)
    
    # Fallback to App Password
    password = GMAIL_APP_PASSWORD
    
    if not use_oauth and not password:
        print('[EMAIL ERROR] No valid Gmail credentials (neither OAuth2 nor App Password) found.')
        return False

    msg = EmailMessage()
    msg['Subject'] = f"AI Investigation Report for volume {investigation_result['volume']}"
    msg['From'] = user
    msg['To'] = user  # sending to self for POC
    msg.set_content(format_email_body(investigation_result))

    if attachment and os.path.isfile(attachment):
        with open(attachment, 'rb') as f:
            file_data = f.read()
            file_name = os.path.basename(attachment)
        msg.add_attachment(file_data, maintype='application', subtype='pdf', filename=file_name)

    context = ssl.create_default_context()
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465, context=context) as server:
            server.ehlo()  # Explicitly identify ourselves to the server
            if use_oauth:
                # OAuth2 Authentication
                auth_string = f"user={user}\1auth=Bearer {access_token}\1\1"
                code, response = server.docmd('AUTH', 'XOAUTH2 ' + base64.b64encode(auth_string.encode()).decode())
                if code != 235:
                    print(f"[OAUTH AUTH ERROR] Code: {code}, Response: {response}")
                    # If OAuth fails, try falling back to App Password if available
                    if password:
                        print("[INFO] Falling back to App Password...")
                        server.login(user, password)
                    else:
                        raise Exception(f"OAuth authentication failed: {response}")
            else:
                # Standard App Password Authentication
                server.login(user, password)
            
            server.send_message(msg)
        print(f"[EMAIL SENT] Report emailed to {user}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False

def send_teams(investigation_result, attachment=None):
    """Send a Microsoft Teams message via Incoming Webhook with the investigation report attached.
    Expects environment variable TEAMS_WEBHOOK_URL.
    """
    webhook_url = os.getenv('TEAMS_WEBHOOK_URL')
    if not webhook_url:
        print('[TEAMS ERROR] TEAMS_WEBHOOK_URL not set in environment.')
        return False
    card = format_teams_card(investigation_result)
    try:
        response = requests.post(webhook_url, json=card)
        if response.status_code == 200:
            print('[TEAMS SENT] Notification posted.')
        else:
            print(f'[TEAMS ERROR] Status {response.status_code}: {response.text}')
    except Exception as e:
        print(f'[TEAMS EXCEPTION] {e}')
        return False
    # Attachment handling is not supported directly by Teams webhook; the PDF is attached via email.
    return True

from reporting import generate_investigation_report

def trigger_alert_flow(investigation_result, config):
    """
    Orchestrates the alerting workflow using AI investigation results.
    """
    actions = []
    
    # Only alert on High Severity for this POC (or config based)
    if investigation_result['severity'] != 'High':
        return actions

    # Generate Detailed PDF Report
    # Uses the new AI-specific report generator
    pdf_path = generate_investigation_report(
        investigation_result, 
        filename=f"AI_Investigation_{investigation_result['id']}.pdf"
    )
    print(f"[REPORT] Generated AI Investigation PDF: {pdf_path}")

    # Check Email Config
    if config.get('enable_email', False):
        # Use real Gmail email sending
        if send_email(investigation_result, attachment=pdf_path):
            actions.append('Email')

    # Check Teams Config
    if config.get('enable_teams', False):
        # Use real Teams webhook
        if send_teams(investigation_result, attachment=pdf_path):
            actions.append('Teams')
            
    # Cleanup temporary PDF report
    if pdf_path and os.path.isfile(pdf_path):
        try:
            os.remove(pdf_path)
            print(f"[CLEANUP] Removed temporary report: {pdf_path}")
        except Exception as e:
            print(f"[CLEANUP ERROR] Could not remove report: {e}")
            
    return actions

def format_email_body(data):
    """
    Formats email using Investigation Result Object structure.
    """
    # Handle both old (row) and new (dict) structures for backward compatibility if needed,
    # but strictly we are checking for 'findings' key for the new AI flow.
    
    if 'findings' in data:
        # AI Result Object
        return f"""
        Subject: AI DETECTED: {data['findings']['primary_cause']} on {data['volume']}
        
        To: Storage Admin Team
        From: NetApp AI Monitor (POC)
        
        AI INVESTIGATION SUMMARY:
        --------------------------------------------------
        Investigation ID: {data['id']}
        Severity:         {data['severity']}
        Volume:           {data['volume']}
        Primary Cause:    {data['findings']['primary_cause']} ({data['findings']['confidence_score']} Confidence)
        Pattern:          {data['analysis']['behavior_pattern']}
        
        AI Reasoning:
        {data['findings']['reasoning']}
        --------------------------------------------------
        
        A detailed PDF report with technical analysis is attached.
        """
    else:
        # Fallback for old simple rows (if any)
        return f"Legacy Alert for {data.get('Volume_Name', 'Unknown')}"

def format_teams_card(data):
    """
    Formats Teams card using Investigation Result Object.
    """
    if 'findings' in data:
        return {
            "@type": "MessageCard",
            "summary": f"AI Alert: {data['findings']['primary_cause']}",
            "sections": [{
                "activityTitle": "AI Performance Investigation",
                "activitySubtitle": f"Volume: {data['volume']} | Severity: {data['severity']}",
                "facts": [
                    {"name": "Cause", "value": data['findings']['primary_cause']},
                    {"name": "Confidence", "value": data['findings']['confidence_score']},
                    {"name": "Pattern", "value": data['analysis']['behavior_pattern']},
                    {"name": "Action", "value": "See Attached PDF"}
                ],
                "text": data['analysis']['description']
            }]
        }
    return {}

if __name__ == "__main__":
    # Simple test to verify email sending
    dummy_result = {
        "id": "test-001",
        "volume": "test_volume",
        "severity": "High",
        "findings": {
            "primary_cause": "Test Cause",
            "confidence_score": "100%",
            "reasoning": "This is a test email."
        },
        "analysis": {
            "behavior_pattern": "Test Pattern",
            "description": "Test description"
        }
    }
    # No PDF attachment needed for this test
    send_email(dummy_result, attachment=None)
