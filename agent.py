import json
import logging
import os
from typing import Any, Dict

from notifier import Notifier
from va_api_client import VAApiClient

class VAClaimAgent:
    def __init__(self, config_file: str = "config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.results_file = self.config.get("results_file", "results.txt")
        self.ensure_results_file()
        self.api_client = VAApiClient(
            mode=self.config.get("mode", "mock"),
            cookies=self.config.get("cookies", {}),
            user_agent=self.config.get("user_agent"),
        )
        self.notifier = Notifier(self.config)

    def load_config(self, config_file: str) -> Dict[str, Any]:
        if os.path.exists(config_file):
            with open(config_file, "r") as f:
                return json.load(f)

        return {
            "mode": "mock",
            "claim_id": "117877436",
            "send_email": False,
            "cookies": {},
            "email": {
                "sender": "your_email@example.com",
                "receiver": "recipient_email@example.com",
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "your_email@example.com",
                "password": "your_password"
            },
            "results_file": "results.txt",
            "log_file": "agent_log.txt"
        }

    def setup_logging(self) -> None:
        logging.basicConfig(
            filename=self.config.get("log_file", "agent_log.txt"),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s"
        )

    def ensure_results_file(self) -> None:
        if not os.path.exists(self.results_file):
            with open(self.results_file, "w") as f:
                f.write("0")

    def check_halt(self) -> bool:
        with open(self.results_file, "r") as f:
            value = f.read().strip()
        if value == "1":
            self.log("Execution halted due to value 1 in results.txt")
            return True
        return False

    def analyze_status(self, data: Dict[str, Any]) -> str:
        status = data.get("status", "Unknown")
        last_updated = data.get("last_updated", "unknown")
        details = data.get("details", "No details available.")
        stage = data.get("stage", "Unknown stage")

        return (
            f"Claim {data.get('claim_id', 'unknown')} is currently '{status}'\n"
            f"Stage: {stage}\n"
            f"Last updated: {last_updated}\n"
            f"Details: {details}"
        )

    def run_check(self) -> None:
        if self.check_halt():
            return

        claim_id = str(self.config.get("claim_id", "117877436"))
        self.log(f"Starting claim status check for claim ID {claim_id}")

        data = self.api_client.get_claim(claim_id)
        analysis = self.analyze_status(data)
        self.log(f"Claim analysis:\n{analysis}")

        if self.api_client.has_update_today(data):
            self.log("Today's date found in claim data — sending notification.")
            self.notifier.notify(analysis)
            with open(self.results_file, "w") as f:
                f.write("1")
        else:
            self.log("No update today; no notification sent.")

    def fetch_claim(self, claim_id: str = None) -> dict:
        claim_id = claim_id or str(self.config.get("claim_id", "117877436"))
        return self.api_client.get_claim(claim_id)

    def get_claim_analysis(self, claim_id: str = None) -> str:
        data = self.fetch_claim(claim_id)
        return self.analyze_status(data)

    def log(self, message: str) -> None:
        logging.info(message)
        print(message)
