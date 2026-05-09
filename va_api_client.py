import time
from datetime import datetime

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from auth import OAuthClient

MOCK_CLAIM_DATA = {
    "117877436": {
        "claim_id": "117877436",
        "status": "Pending",
        "last_updated": "2026-05-01",
        "details": "Claim is under review.",
        "stage": "Evidence Gathering",
        "estimated_decision_date": None,
    },
    "default": {
        "claim_id": "default",
        "status": "Pending",
        "last_updated": "2026-05-01",
        "details": "Claim is under review.",
        "stage": "Evidence Gathering",
        "estimated_decision_date": None,
    },
}

BASE_URLS = {
    "real":    "https://api.va.gov",
    "sandbox": "https://sandbox-api.va.gov",
}

# Retry on transient server errors and rate-limit responses.
_RETRY_CONFIG = Retry(
    total=4,
    backoff_factor=2,          # waits: 2s, 4s, 8s, 16s
    status_forcelist={429, 500, 502, 503, 504},
    allowed_methods={"GET", "POST"},
    raise_on_status=False,
)


def _session() -> requests.Session:
    s = requests.Session()
    adapter = HTTPAdapter(max_retries=_RETRY_CONFIG)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


class VAApiClient:
    def __init__(self, mode="mock", environment="sandbox", oauth_config=None,
                 cookies=None, user_agent=None):
        self.mode = mode
        self.environment = environment
        self.base_url = BASE_URLS.get(environment, BASE_URLS["sandbox"])
        self.cookies = cookies or {}
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.6943.141 Safari/537.36"
        )
        self.oauth = None
        if oauth_config and oauth_config.get("client_id") not in (None, "YOUR_CLIENT_ID", ""):
            self.oauth = OAuthClient(
                client_id=oauth_config["client_id"],
                client_secret=oauth_config["client_secret"],
                environment=environment,
            )
        self._session = _session()

    def _headers(self) -> dict:
        headers = {"User-Agent": self.user_agent}
        if self.oauth:
            headers["Authorization"] = f"Bearer {self.oauth.get_access_token()}"
        return headers

    def _get(self, url: str) -> requests.Response:
        kwargs = {"headers": self._headers()}
        if not self.oauth:
            kwargs["cookies"] = self.cookies
        resp = self._session.get(url, **kwargs)
        resp.raise_for_status()
        return resp

    def get_claim(self, claim_id: str, veteran_id: str = None) -> dict:
        if self.mode == "mock":
            return MOCK_CLAIM_DATA.get(claim_id, MOCK_CLAIM_DATA["default"])
        return self.get_claim_real(claim_id, veteran_id)

    def get_claim_real(self, claim_id: str, veteran_id: str = None) -> dict:
        if veteran_id:
            url = f"{self.base_url}/services/claims/v2/veterans/{veteran_id}/claims/{claim_id}"
        else:
            url = f"{self.base_url}/v0/benefits_claims/{claim_id}"
        return self._get(url).json()

    def list_claims(self, veteran_id: str = None) -> list:
        if self.mode == "mock":
            return list(MOCK_CLAIM_DATA.values())
        if veteran_id:
            url = f"{self.base_url}/services/claims/v2/veterans/{veteran_id}/claims"
        else:
            url = f"{self.base_url}/v0/benefits_claims"
        data = self._get(url).json()
        return data.get("data", data) if isinstance(data, dict) else data

    def has_update_today(self, data: dict) -> bool:
        today_str = datetime.now().strftime("%Y-%m-%d")
        return today_str in str(data)
