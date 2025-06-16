import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# API endpoint
url = "https://api.va.gov/v0/benefits_claims/8008135"

# Define headers
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
authorization_token = "Bearer YOUR_ACCESS_TOKEN"

headers = {
    "User-Agent": user_agent,
    "Authorization": authorization_token
}

# Send GET request
response = requests.get(url, headers=headers)

# Check response status
if response.status_code == 200:
    data = response.json()
    print("JSON data received successfully.")

    # Get today's date
    today_str = datetime.now().strftime("%Y-%m-%d")

    # Search for today's date in JSON data
    data_str = str(data)
    if today_str in data_str:
        print(f"Today's date ({today_str}) found in JSON data.")

        # Email details
        sender_email = "your_email@example.com"
        receiver_email = "recipient_email@example.com"
        smtp_server = "smtp.example.com"
        smtp_port = 587
        smtp_username = "your_email@example.com"
        smtp_password = "your_password"

        # Create the email content
        msg = MIMEText(f"Today's date ({today_str}) found in JSON data.")
        msg['Subject'] = "Date Found Notification"
        msg['From'] = sender_email
        msg['To'] = receiver_email

        # Send the email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_username, smtp_password)
            server.send_message(msg)
            print("Email notification sent successfully.")
    else:
        print(f"Today's date ({today_str}) not found in JSON data.")
else:
    print(f"Request failed with status code: {response.status_code}")
