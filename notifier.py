import logging
import smtplib
from email.mime.text import MIMEText

class Notifier:
    def __init__(self, config: dict):
        self.config = config
        self.send_email = config.get("send_email", False)

    def notify(self, message: str) -> None:
        if not self.send_email:
            logging.info("Mock notification: %s", message)
            print(f"Mock notification: {message}")
            return

        email_config = self.config.get("email", {})
        msg = MIMEText(message)
        msg["Subject"] = "VA Claim Status Update"
        msg["From"] = email_config.get("sender")
        msg["To"] = email_config.get("receiver")

        with smtplib.SMTP(email_config.get("smtp_server"), email_config.get("smtp_port")) as server:
            server.starttls()
            server.login(email_config.get("username"), email_config.get("password"))
            server.send_message(msg)

        logging.info("Email notification sent.")
