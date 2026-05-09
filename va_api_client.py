from datetime import datetime
import requests

MOCK_CLAIM_DATA = {
    "117877436": {
        "claim_id": "117877436",
        "status": "Pending",
        "last_updated": "2026-05-01",
        "details": "Claim is under review.",
        "stage": "Evidence Gathering"
    },
    "default": {
        "claim_id": "default",
        "status": "Pending",
        "last_updated": "2026-05-01",
        "details": "Claim is under review.",
        "stage": "Evidence Gathering"
    }
}

class VAApiClient:
    def __init__(self, mode="mock", base_url="https://api.va.gov", cookies=None, user_agent=None):
        self.mode = mode
        self.base_url = base_url
        self.cookies = cookies or {}
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.6943.141 Safari/537.36"
        )

    def get_claim(self, claim_id: str) -> dict:
        if self.mode == "mock":
            return MOCK_CLAIM_DATA.get(claim_id, MOCK_CLAIM_DATA["default"])
        return self.get_claim_real(claim_id)

    def get_claim_real(self, claim_id: str) -> dict:
        url = f"{self.base_url}/v0/benefits_claims/{claim_id}"
        headers = {"User-Agent": self.user_agent}
        response = requests.get(url, headers=headers, cookies=self.cookies)
        response.raise_for_status()
        return response.json()

    def has_update_today(self, data: dict) -> bool:
        today_str = datetime.now().strftime("%Y-%m-%d")
        return today_str in str(data)

    def list_claims(self, veteran_id: str) -> list:
        if self.mode == "mock":
            return [MOCK_CLAIM_DATA.get("117877436")]
        raise NotImplementedError("Claim listing is not implemented yet.")
