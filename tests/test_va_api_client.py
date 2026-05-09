import time
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from va_api_client import VAApiClient


@pytest.fixture
def mock_client():
    return VAApiClient(mode="mock")


@pytest.fixture
def real_client():
    return VAApiClient(mode="real", environment="sandbox")


class TestGetClaimMock:
    def test_known_claim_id(self, mock_client):
        result = mock_client.get_claim("117877436")
        assert result["claim_id"] == "117877436"

    def test_known_claim_status(self, mock_client):
        result = mock_client.get_claim("117877436")
        assert result["status"] == "Pending"

    def test_unknown_id_returns_default(self, mock_client):
        result = mock_client.get_claim("000000")
        assert result["claim_id"] == "default"

    def test_default_stage(self, mock_client):
        result = mock_client.get_claim("117877436")
        assert result["stage"] == "Evidence Gathering"


class TestListClaimsMock:
    def test_returns_list(self, mock_client):
        result = mock_client.list_claims()
        assert isinstance(result, list)

    def test_contains_known_claim(self, mock_client):
        result = mock_client.list_claims()
        ids = [c["claim_id"] for c in result]
        assert "117877436" in ids

    def test_returns_multiple_claims(self, mock_client):
        result = mock_client.list_claims()
        assert len(result) >= 2


class TestHasUpdateToday:
    def test_true_when_today_in_data(self, mock_client):
        today = datetime.now().strftime("%Y-%m-%d")
        assert mock_client.has_update_today({"last_updated": today}) is True

    def test_false_when_old_date(self, mock_client):
        assert mock_client.has_update_today({"last_updated": "2020-01-01"}) is False

    def test_true_when_date_nested_deep(self, mock_client):
        today = datetime.now().strftime("%Y-%m-%d")
        data = {"attributes": {"claimPhaseDates": {"phaseChangeDate": today}}}
        assert mock_client.has_update_today(data) is True

    def test_false_for_empty_dict(self, mock_client):
        assert mock_client.has_update_today({}) is False


class TestHeaders:
    def test_user_agent_always_set(self):
        client = VAApiClient(mode="mock", user_agent="TestBot/1.0")
        assert client._headers()["User-Agent"] == "TestBot/1.0"

    def test_no_authorization_without_oauth(self, mock_client):
        assert "Authorization" not in mock_client._headers()

    def test_authorization_header_with_oauth(self, tmp_path):
        from auth import TokenStore
        client = VAApiClient(
            mode="real",
            oauth_config={"client_id": "real-id", "client_secret": "real-secret"},
        )
        store = TokenStore(str(tmp_path / "tokens.json"))
        store.save({"access_token": "bearer-tok", "expires_at": time.time() + 3600})
        client.oauth.store = store
        assert client._headers()["Authorization"] == "Bearer bearer-tok"

    def test_placeholder_client_id_skips_oauth(self):
        client = VAApiClient(
            mode="real",
            oauth_config={"client_id": "YOUR_CLIENT_ID", "client_secret": "secret"},
        )
        assert client.oauth is None


class TestGetClaimReal:
    def test_uses_legacy_url_without_veteran_id(self, real_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        with patch.object(real_client, "_get", return_value=mock_resp) as m:
            real_client.get_claim_real("123")
        assert "/v0/benefits_claims/123" in m.call_args[0][0]

    def test_uses_v2_url_with_veteran_id(self, real_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        with patch.object(real_client, "_get", return_value=mock_resp) as m:
            real_client.get_claim_real("123", veteran_id="V001")
        assert "/services/claims/v2/veterans/V001/claims/123" in m.call_args[0][0]

    def test_includes_sandbox_base_url(self, real_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {}
        with patch.object(real_client, "_get", return_value=mock_resp) as m:
            real_client.get_claim_real("123")
        assert "sandbox-api.va.gov" in m.call_args[0][0]

    def test_returns_parsed_json(self, real_client):
        payload = {"data": {"id": "123"}}
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        with patch.object(real_client, "_get", return_value=mock_resp):
            result = real_client.get_claim_real("123")
        assert result == payload


class TestListClaimsReal:
    def test_uses_v2_url_with_veteran_id(self, real_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": []}
        with patch.object(real_client, "_get", return_value=mock_resp) as m:
            real_client.list_claims(veteran_id="V001")
        assert "/services/claims/v2/veterans/V001/claims" in m.call_args[0][0]

    def test_uses_legacy_url_without_veteran_id(self, real_client):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        with patch.object(real_client, "_get", return_value=mock_resp) as m:
            real_client.list_claims()
        assert "/v0/benefits_claims" in m.call_args[0][0]

    def test_unwraps_data_envelope(self, real_client):
        claims = [{"id": "1"}, {"id": "2"}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"data": claims}
        with patch.object(real_client, "_get", return_value=mock_resp):
            result = real_client.list_claims()
        assert result == claims

    def test_handles_bare_list_response(self, real_client):
        claims = [{"id": "1"}]
        mock_resp = MagicMock()
        mock_resp.json.return_value = claims
        with patch.object(real_client, "_get", return_value=mock_resp):
            result = real_client.list_claims()
        assert result == claims


class TestRetryConfiguration:
    def test_retry_total_is_four(self, mock_client):
        adapter = mock_client._session.get_adapter("https://")
        assert adapter.max_retries.total == 4

    def test_retries_on_429(self, mock_client):
        adapter = mock_client._session.get_adapter("https://")
        assert 429 in adapter.max_retries.status_forcelist

    def test_retries_on_500(self, mock_client):
        adapter = mock_client._session.get_adapter("https://")
        assert 500 in adapter.max_retries.status_forcelist

    def test_retries_on_503(self, mock_client):
        adapter = mock_client._session.get_adapter("https://")
        assert 503 in adapter.max_retries.status_forcelist

    def test_backoff_factor_is_two(self, mock_client):
        adapter = mock_client._session.get_adapter("https://")
        assert adapter.max_retries.backoff_factor == 2
