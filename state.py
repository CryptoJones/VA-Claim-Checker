"""
Persists the last-known claim state so the agent can detect any phase
transition across runs, not just the first one.

State file format (JSON):
{
  "117877436": {
    "status": "PENDING",
    "stage": "Evidence Gathering",
    "last_updated": "2026-05-01",
    "notified_at": "2026-05-09T10:30:00"
  }
}
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

STATE_FILE = ".va_state.json"


class StateStore:
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file

    def _load_all(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            with open(self.state_file) as f:
                return json.load(f)
        return {}

    def _save_all(self, data: Dict[str, Any]) -> None:
        with open(self.state_file, "w") as f:
            json.dump(data, f, indent=2)

    def get(self, claim_id: str) -> Optional[Dict[str, Any]]:
        return self._load_all().get(str(claim_id))

    def save(self, claim_id: str, claim: Dict[str, Any]) -> None:
        all_state = self._load_all()
        all_state[str(claim_id)] = {
            "status": claim.get("status"),
            "stage": claim.get("stage"),
            "last_updated": claim.get("last_updated"),
            "estimated_decision_date": claim.get("estimated_decision_date"),
            "notified_at": datetime.now().isoformat(timespec="seconds"),
        }
        self._save_all(all_state)

    def has_changed(self, claim_id: str, claim: Dict[str, Any]) -> bool:
        prev = self.get(claim_id)
        if prev is None:
            return True
        return (
            prev.get("status") != claim.get("status")
            or prev.get("stage") != claim.get("stage")
            or prev.get("last_updated") != claim.get("last_updated")
        )

    def diff_summary(self, claim_id: str, claim: Dict[str, Any]) -> str:
        prev = self.get(claim_id)
        if prev is None:
            return "First time checking this claim."
        lines = []
        if prev.get("status") != claim.get("status"):
            lines.append(f"Status:  {prev['status']} → {claim['status']}")
        if prev.get("stage") != claim.get("stage"):
            lines.append(f"Stage:   {prev['stage']} → {claim['stage']}")
        if prev.get("last_updated") != claim.get("last_updated"):
            lines.append(f"Updated: {prev['last_updated']} → {claim['last_updated']}")
        return "\n".join(lines) if lines else "No changes detected."

    def reset(self, claim_id: str = None) -> None:
        if claim_id:
            all_state = self._load_all()
            all_state.pop(str(claim_id), None)
            self._save_all(all_state)
        elif os.path.exists(self.state_file):
            os.remove(self.state_file)
