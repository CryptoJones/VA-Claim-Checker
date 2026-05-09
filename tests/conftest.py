import json
import pytest


@pytest.fixture
def base_claim():
    return {
        "claim_id": "117877436",
        "claim_type": "Compensation",
        "status": "Pending",
        "stage": "Evidence Gathering",
        "last_updated": "2026-05-01",
        "estimated_decision_date": None,
        "close_date": None,
        "decision_letter_sent": False,
        "documents_needed": False,
        "phase_went_back": False,
        "contentions": "None listed",
        "details": "Claim is under review.",
    }


@pytest.fixture
def tmp_config(tmp_path):
    cfg = {
        "mode": "mock",
        "environment": "sandbox",
        "claim_id": "117877436",
        "send_email": False,
        "oauth": {"client_id": "", "client_secret": ""},
        "cookies": {},
        "email": {
            "sender": "from@test.com",
            "receiver": "to@test.com",
            "smtp_server": "smtp.test.com",
            "smtp_port": 587,
            "username": "from@test.com",
            "password": "secret",
        },
        "push": {"enabled": False, "provider": "ntfy", "topic": "test-topic", "token": ""},
        "state_file": str(tmp_path / ".va_state.json"),
        "log_file": str(tmp_path / "test.log"),
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(cfg))
    return str(path), cfg, tmp_path
