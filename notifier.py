import logging
import os
import smtplib
from email.mime.text import MIMEText


def _resolve(config_value: str, env_var: str) -> str:
    return os.environ.get(env_var) or config_value or ""


class Notifier:
    def __init__(self, config: dict):
        self.config = config
        self.send_email = config.get("send_email", False)
        self.push = config.get("push", {})

    def notify(self, message: str, claim_id: str = "") -> None:
        subject = f"VA Claim {claim_id} Update" if claim_id else "VA Claim Status Update"
        if self.send_email:
            self._send_email(subject, message)
        if self.push.get("enabled"):
            self._send_push(subject, message)
        if not self.send_email and not self.push.get("enabled"):
            logging.info("Mock notification: %s", message)
            print(f"[mock notification]\n{message}")

    def _send_email(self, subject: str, message: str) -> None:
        ec = self.config.get("email", {})
        password = _resolve(ec.get("password", ""), "VA_SMTP_PASSWORD")
        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = ec.get("sender")
        msg["To"] = ec.get("receiver")
        with smtplib.SMTP(ec.get("smtp_server"), ec.get("smtp_port", 587)) as server:
            server.starttls()
            server.login(ec.get("username"), password)
            server.send_message(msg)
        logging.info("Email notification sent.")

    def _send_push(self, subject: str, message: str) -> None:
        provider = self.push.get("provider", "ntfy")
        if provider == "ntfy":
            self._ntfy(subject, message)
        elif provider == "pushover":
            self._pushover(subject, message)

    def _ntfy(self, subject: str, message: str) -> None:
        import requests
        topic = self.push.get("topic", "va-claim-checker")
        url = f"https://ntfy.sh/{topic}"
        token = _resolve(self.push.get("token", ""), "VA_NTFY_TOKEN")
        headers = {"Title": subject}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        resp = requests.post(url, data=message.encode(), headers=headers)
        resp.raise_for_status()
        logging.info("ntfy push notification sent.")

    def _pushover(self, subject: str, message: str) -> None:
        import requests
        token = _resolve(self.push.get("app_token", ""), "VA_PUSHOVER_APP_TOKEN")
        user = _resolve(self.push.get("user_key", ""), "VA_PUSHOVER_USER_KEY")
        resp = requests.post("https://api.pushover.net/1/messages.json", data={
            "token": token,
            "user": user,
            "title": subject,
            "message": message,
        })
        resp.raise_for_status()
        logging.info("Pushover notification sent.")
