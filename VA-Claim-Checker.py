import os
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText

# Check or create results.txt
results_file = "results.txt"
if os.path.exists(results_file):
    with open(results_file, "r") as f:
        value = f.read().strip()
        if value == "1":
            print("Execution halted due to value 1 in results.txt")
            exit()
else:
    with open(results_file, "w") as f:
        f.write("0")

# API endpoint
url = "https://api.va.gov/v0/benefits_claims/8008135"

# UserAgent
user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36"
# _ga (QTY 3)
VACookie_ga="MYCOOKIEDATA"
VACookie__ga_CSLL4ZEK4L="MYCOOKIEDATA"
VACookie_ga_YPB3FD0PQ9="MYCOOKIEDATA"
# TSXXXXXXXX (QTY 3)
VACookieTS01f27c67="MYCOOKIEDATA"
VACookieTS0189a5f9="MYCOOKIEDATA"
VACookieTS014c0a39="MYCOOKIEDATA"
# Other VA Cookies (QTY 3)
VACookieapi_session="MYCOOKIEDATA"
VACookieCERNER_ELIGIBLE="MYCOOKIEDATA"
VACookievagov_saml_request_prod="MYCOOKIEDATA"

headers = {
    "User-Agent": user_agent,
    "_ga": VACookie_ga,
    "__ga_CSLL4ZEK4L": VACookie__ga_CSLL4ZEK4L,
    "_ga_YPB3FD0PQ9": VACookie_ga_YPB3FD0PQ9,
    "TS01f27c67": VACookieTS01f27c67,
    "TS0189a5f9": VACookieTS0189a5f9,
    "TS014c0a39": VACookieTS014c0a39,
    "api_session": VACookieapi_session,
    "CERNER_ELIGIBLE": VACookieCERNER_ELIGIBLE,
    "vagov_saml_request_prod": VACookievagov_saml_request_prod
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
