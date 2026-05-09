import json
import logging
import os
from typing import Any, Dict, List

from notifier import Notifier
from state import StateStore
from va_api_client import VAApiClient
from va_response_parser import normalize


class VAClaimAgent:
    def __init__(self, config_file: str = "config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        self.state = StateStore(self.config.get("state_file", ".va_state.json"))
        self.api_client = VAApiClient(
            mode=self.config.get("mode", "mock"),
            environment=self.config.get("environment", "sandbox"),
            oauth_config=self.config.get("oauth"),
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
            "environment": "sandbox",
            "claim_id": "117877436",
            "send_email": False,
            "oauth": {"client_id": "", "client_secret": ""},
            "cookies": {},
            "email": {
                "sender": "your_email@example.com",
                "receiver": "recipient_email@example.com",
                "smtp_server": "smtp.example.com",
                "smtp_port": 587,
                "username": "your_email@example.com",
                "password": "your_password",
            },
            "state_file": ".va_state.json",
            "log_file": "agent_log.txt",
        }

    def setup_logging(self) -> None:
        logging.basicConfig(
            filename=self.config.get("log_file", "agent_log.txt"),
            level=logging.INFO,
            format="%(asctime)s - %(levelname)s - %(message)s",
        )

    def analyze_status(self, claim: Dict[str, Any]) -> str:
        lines = [
            f"Claim {claim['claim_id']} — {claim.get('claim_type', 'Compensation')}",
            f"Status:   {claim['status']}",
            f"Stage:    {claim['stage']}",
            f"Updated:  {claim['last_updated']}",
        ]
        if claim.get("estimated_decision_date"):
            lines.append(f"Est. decision date: {claim['estimated_decision_date']}")
        if claim.get("decision_letter_sent"):
            lines.append("Decision letter has been sent.")
        if claim.get("documents_needed"):
            lines.append("Action required: VA needs additional documents.")
        if claim.get("phase_went_back"):
            lines.append("Note: claim was returned to a previous phase.")
        if claim.get("contentions") and claim["contentions"] != "None listed":
            lines.append(f"Contentions: {claim['contentions']}")
        return "\n".join(lines)

    def _check_one(self, claim_id: str) -> None:
        self.log(f"Checking claim {claim_id}")
        raw = self.api_client.get_claim(claim_id)
        claim = normalize(raw)
        analysis = self.analyze_status(claim)
        self.log(f"Analysis:\n{analysis}")

        if self.state.has_changed(claim_id, claim):
            diff = self.state.diff_summary(claim_id, claim)
            self.log(f"Change detected:\n{diff}")
            message = f"{analysis}\n\n--- What changed ---\n{diff}"
            self.notifier.notify(message, claim_id=claim_id)
            self.state.save(claim_id, claim)
        else:
            self.log(f"No change for claim {claim_id}.")

    def run_check(self, claim_ids: List[str] = None) -> None:
        ids = claim_ids or self._configured_claim_ids()
        for claim_id in ids:
            self._check_one(str(claim_id))

    def _configured_claim_ids(self) -> List[str]:
        raw = self.config.get("claim_id", "117877436")
        if isinstance(raw, list):
            return [str(c) for c in raw]
        return [str(raw)]

    def fetch_claim(self, claim_id: str = None) -> dict:
        claim_id = claim_id or self._configured_claim_ids()[0]
        return normalize(self.api_client.get_claim(claim_id))

    def get_claim_analysis(self, claim_id: str = None) -> str:
        return self.analyze_status(self.fetch_claim(claim_id))

    def list_claims(self, veteran_id: str = None) -> List[dict]:
        raw_list = self.api_client.list_claims(veteran_id)
        return [normalize(item) for item in raw_list]

    def log(self, message: str) -> None:
        logging.info(message)
        print(message)
