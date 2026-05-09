import time
import pytest
from unittest.mock import patch, MagicMock

from auth import TokenStore, OAuthClient, resolve_secret


@pytest.fixture
def store(tmp_path):
    return TokenStore(str(tmp_path / "tokens.json"))


@pytest.fixture
def fresh_tokens():
    return {"access_token": "tok-abc", "refresh_token": "ref-xyz", "expires_at": time.time() + 3600}


@pytest.fixture
def expired_tokens():
    return {"access_token": "tok-old", "refresh_token": "ref-old", "expires_at": time.time() - 10}


class TestTokenStoreLoad:
    def test_returns_empty_dict_when_no_file(self, store):
        assert store.load() == {}

    def test_returns_saved_data(self, store, fresh_tokens):
        store.save(fresh_tokens)
        loaded = store.load()
        assert loaded["access_token"] == "tok-abc"

    def test_preserves_all_fields(self, store, fresh_tokens):
        store.save(fresh_tokens)
        loaded = store.load()
        assert set(loaded.keys()) == set(fresh_tokens.keys())


class TestTokenStoreSave:
    def test_file_created(self, store, fresh_tokens, tmp_path):
        store.save(fresh_tokens)
        assert (tmp_path / "tokens.json").exists()

    def test_file_permissions_are_600(self, store, fresh_tokens, tmp_path):
        store.save(fresh_tokens)
        mode = oct((tmp_path / "tokens.json").stat().st_mode)[-3:]
        assert mode == "600"

    def test_overwrites_existing(self, store, fresh_tokens):
        store.save(fresh_tokens)
        store.save({**fresh_tokens, "access_token": "tok-new"})
        assert store.load()["access_token"] == "tok-new"


class TestTokenStoreClear:
    def test_removes_file(self, store, fresh_tokens, tmp_path):
        store.save(fresh_tokens)
        store.clear()
        assert not (tmp_path / "tokens.json").exists()

    def test_safe_when_no_file(self, store):
        store.clear()  # should not raise


class TestTokenStoreIsValid:
    def test_false_when_empty(self, store):
        assert store.is_valid() is False

    def test_false_when_no_access_token(self, store):
        store.save({"expires_at": time.time() + 3600})
        assert store.is_valid() is False

    def test_false_when_expired(self, store, expired_tokens):
        store.save(expired_tokens)
        assert store.is_valid() is False

    def test_false_within_60s_buffer(self, store):
        store.save({"access_token": "tok", "expires_at": time.time() + 30})
        assert store.is_valid() is False

    def test_true_when_fresh(self, store, fresh_tokens):
        store.save(fresh_tokens)
        assert store.is_valid() is True


class TestResolveSecret:
    def test_env_var_takes_priority(self, monkeypatch):
        monkeypatch.setenv("VA_CLIENT_ID", "from-env")
        assert resolve_secret("from-config", "VA_CLIENT_ID") == "from-env"

    def test_falls_back_to_config(self, monkeypatch):
        monkeypatch.delenv("VA_CLIENT_ID", raising=False)
        assert resolve_secret("from-config", "VA_CLIENT_ID") == "from-config"

    def test_returns_empty_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("VA_CLIENT_ID", raising=False)
        assert resolve_secret("", "VA_CLIENT_ID") == ""

    def test_env_var_overrides_nonempty_config(self, monkeypatch):
        monkeypatch.setenv("VA_CLIENT_ID", "env-wins")
        assert resolve_secret("config-value", "VA_CLIENT_ID") == "env-wins"


class TestOAuthClientGetAccessToken:
    def test_returns_stored_token_when_valid(self, tmp_path, fresh_tokens):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        client.store.save(fresh_tokens)
        assert client.get_access_token() == "tok-abc"

    def test_calls_refresh_when_expired_with_refresh_token(self, tmp_path, expired_tokens):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        client.store.save(expired_tokens)
        with patch.object(client, "_refresh", return_value="refreshed-tok") as mock_refresh:
            token = client.get_access_token()
        mock_refresh.assert_called_once_with("ref-old")
        assert token == "refreshed-tok"

    def test_falls_back_to_authorize_when_refresh_fails(self, tmp_path, expired_tokens):
        import requests as req
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        client.store.save(expired_tokens)
        with patch.object(client, "_refresh", side_effect=req.HTTPError("401")):
            with patch.object(client, "_authorize", return_value="auth-tok") as mock_auth:
                token = client.get_access_token()
        mock_auth.assert_called_once()
        assert token == "auth-tok"

    def test_calls_authorize_when_no_tokens(self, tmp_path):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        with patch.object(client, "_authorize", return_value="new-tok") as mock_auth:
            token = client.get_access_token()
        mock_auth.assert_called_once()
        assert token == "new-tok"


class TestOAuthClientSave:
    def test_stores_access_token(self, tmp_path):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        result = client._save({"access_token": "tok", "expires_in": 3600})
        assert result == "tok"

    def test_calculates_expires_at(self, tmp_path):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        before = time.time()
        client._save({"access_token": "tok", "expires_in": 3600})
        after = time.time()
        saved = client.store.load()
        assert before + 3600 - 1 <= saved["expires_at"] <= after + 3600 + 1

    def test_defaults_expires_in_to_3600(self, tmp_path):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        before = time.time()
        client._save({"access_token": "tok"})
        saved = client.store.load()
        assert saved["expires_at"] >= before + 3599


class TestOAuthClientAuthorize:
    def _client(self, tmp_path, **kwargs):
        c = OAuthClient("cid", "secret", "sandbox", **kwargs)
        c.store = TokenStore(str(tmp_path / "tokens.json"))
        return c

    def _mock_server(self, auth_code=None, error=None, timeout=False):
        """Return a mock HTTPServer that simulates a browser callback."""
        from auth import _CallbackHandler
        import auth as auth_mod

        server = MagicMock()

        def handle_request():
            if not timeout:
                _CallbackHandler.auth_code = auth_code
                _CallbackHandler.error = error

        server.handle_request.side_effect = handle_request
        return server

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_successful_auth_no_mfa(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(auth_code="code-abc")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok") as mock_ex:
            result = client._authorize()
        mock_ex.assert_called_once_with("code-abc")
        assert result == "tok"
        mock_browser.assert_called_once()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_successful_auth_after_mfa(self, mock_http, mock_browser, tmp_path):
        """MFA adds delay but the callback eventually arrives — should succeed."""
        client = self._client(tmp_path)
        server = self._mock_server(auth_code="code-mfa")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok-mfa"):
            result = client._authorize()
        assert result == "tok-mfa"
        assert server.timeout == 300

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_timeout_raises_clear_error(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(timeout=True)
        mock_http.return_value = server
        with pytest.raises(RuntimeError, match="timed out"):
            client._authorize()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_provider_error_raises(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(error="access_denied")
        mock_http.return_value = server
        with pytest.raises(RuntimeError, match="access_denied"):
            client._authorize()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer", side_effect=OSError("Address already in use"))
    def test_port_conflict_raises_clear_error(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        with pytest.raises(RuntimeError, match="8080"):
            client._authorize()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_server_closed_after_success(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(auth_code="code-abc")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok"):
            client._authorize()
        server.server_close.assert_called_once()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_server_closed_after_timeout(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(timeout=True)
        mock_http.return_value = server
        with pytest.raises(RuntimeError):
            client._authorize()
        server.server_close.assert_called_once()

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_idp_included_in_auth_url(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path, idp="logingov")
        server = self._mock_server(auth_code="code-abc")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok"):
            client._authorize()
        url = mock_browser.call_args[0][0]
        assert "idp=logingov" in url

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_idme_idp_included_in_auth_url(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path, idp="idme")
        server = self._mock_server(auth_code="code-abc")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok"):
            client._authorize()
        url = mock_browser.call_args[0][0]
        assert "idp=idme" in url

    @patch("auth.webbrowser.open")
    @patch("auth.HTTPServer")
    def test_no_idp_omits_param(self, mock_http, mock_browser, tmp_path):
        client = self._client(tmp_path)
        server = self._mock_server(auth_code="code-abc")
        mock_http.return_value = server
        with patch.object(client, "_exchange_code", return_value="tok"):
            client._authorize()
        url = mock_browser.call_args[0][0]
        assert "idp=" not in url


class TestOAuthClientLogout:
    def test_clears_token_store(self, tmp_path, fresh_tokens, capsys):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        client.store.save(fresh_tokens)
        client.logout()
        assert not (tmp_path / "tokens.json").exists()

    def test_prints_confirmation(self, tmp_path, capsys):
        client = OAuthClient("id", "secret", "sandbox")
        client.store = TokenStore(str(tmp_path / "tokens.json"))
        client.logout()
        assert "Logged out" in capsys.readouterr().out
