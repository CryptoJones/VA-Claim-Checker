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
VACookie_ga="GA1.1.1988673135.1747792621"
VACookie__ga_CSLL4ZEK4L="GS2.1.s1750144945$o18$g1$t1750146137$j60$l0$h0"
VACookie_ga_YPB3FD0PQ9="GS2.1.s1750144944$o27$g1$t1750146138$j59$l0$h0"
# TSXXXXXXXX (QTY 3)
VACookieTS01f27c67="0119a2687fc563f9ffcae53b6d70857db09d5431bc3965346cd029072de3e5ade07de5ca52aa9ecb025f1e83133bc2ade799201525"
VACookieTS0189a5f9="0119a2687fc563f9ffcae53b6d70857db09d5431bc3965346cd029072de3e5ade07de5ca52aa9ecb025f1e83133bc2ade799201525"
VACookieTS014c0a39="0119a2687fc563f9ffcae53b6d70857db09d5431bc3965346cd029072de3e5ade07de5ca52aa9ecb025f1e83133bc2ade799201525"
# Other VA Cookies
VACookieapi_session="qwbMWfKi0ILTvFz3aBd6hH4RUW8AeyJ7K8pT8jMJtkNiFX7bUqwhtp4ZK8%2BoWTVLH56lEgdpfviSYAgfmedGSnBnhJAUeuvQl1gRwTPBo1AtphQnKGGJy4VSstrbVywTtaH%2BiDQgPnR3x%2FgTdDiQ%2FtTwdXbgXZM0%2BKSUtz6WomgM1xrJeBufjkfKwmdMp6JXEGgKrFkc%2F7ngOxtjhabIEJ3Dp%2BQbuO0P2ppw0b6weumNulthGdNiQFTdXzbhjJT0AIeMPOzZJH%2B%2FGSj8yuV%2Bl9grE8k56wESmFYJGH43lpooi4U7yDheuvmx%2FvX0Itw6tYnktPrUaP9CHuUm%2FlR9XlOvFhOurzyoSut6aQFHLUoemcQfbW1tnYZiukKCOJ4NzM9IQFwwtQYteejwr%2FU5eCci5KTdy2b4eo%2Bt46jdTB%2B9XyJ8ppgIPRGZ6akUVnkIHT8KOfQU50kUcmL8ruYCNOxQBoRSdBQbbzPPZOcVyEPdHO4sZAEYWvG8Z59uRSaJm%2FbVmpj8myFK3c1fJ9WuknymCK9VUk%2Bxz5IFJ%2Bzn7Q7Itev7BOFELi%2FtVKbrdv0hIDr1mfb%2B0zsXyzJxQQ1aBCXGykQKr2sJ3zUFug5WfvRxSsd4YBBkz0NbS2XuvmEuVVb4Ng86rTMtMzygV5MIvdPGq1BwsiIS9IClpIYyWqLIYmvyw6zHhDW7ZtPHmWUG5Rh1L0S8qXLKOjduxWZREap5S%2BzVedtUuJJOJpSt4K3rTx%2BCTaFE0eAUMcUKTG4ssqPbxzWLI%2BhTWKcwCqhAcEo3cyVzMuwu23R3--gWD3GUJ5%2Bpe1z6ei--mbnvvXOCL5ida%2FgsQOxMmQ%3D%3D"
VACookieCERNER_ELIGIBLE="eyJfcmFpbHMiOnsibWVzc2FnZSI6IkJBaEciLCJleHAiOiIyMDQ1LTA2LTE3VDA3OjI0OjA4LjIwNloiLCJwdXIiOiJjb29raWUuQ0VSTkVSX0VMSUdJQkxFIn19--45124c0bc175c4f0c0d5fab4b0cbe3cfa69bc086"
VACookievagov_saml_request_prod=""

headers = {
    "User-Agent": user_agent,
    "_ga": VACookie_ga,
    "__ga_CSLL4ZEK4L": VACookie__ga_CSLL4ZEK4L,
    "_ga_YPB3FD0PQ9": VACookie_ga_YPB3FD0PQ9,
    "TS01f27c67": VACookieTS01f27c67,
    "TS0189a5f9": VACookieTS0189a5f9,
    "TS014c0a39": VACookieTS014c0a39,
    "CERNER_ELIGIBLE": VACookieCERNER_ELIGIBLE,
    "api_session": VACookieapi_session,
    "vagov_saml_request_prod": VACookievagov_saml_request_prod,


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
