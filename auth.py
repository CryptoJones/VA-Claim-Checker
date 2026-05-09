import base64
import hashlib
import json
import os
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs
from typing import Optional

import requests

KEYRING_SERVICE = "va-claim-checker"


def _keyring_get(key: str) -> Optional[str]:
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, key)
    except Exception:
        return None


def _keyring_set(key: str, value: str) -> None:
    try:
        import keyring
        keyring.set_password(KEYRING_SERVICE, key, value)
    except Exception:
        pass


def resolve_secret(config_value: str, env_var: str) -> str:
    """Return the first non-empty value from: env var → keyring → config file."""
    return (
        os.environ.get(env_var)
        or _keyring_get(env_var)
        or config_value
        or ""
    )

TOKEN_FILE = ".va_tokens.json"
REDIRECT_URI = "http://localhost:8080/callback"
SCOPES = "claim.read openid offline_access"

# Public client ID for real-mode PKCE flow (no client_secret required).
# Users authenticate via their VA.gov account (login.gov) — no developer
# registration needed.
REAL_CLIENT_ID = os.environ.get("VA_CLIENT_ID", "")

ENDPOINTS = {
    "real": {
        "auth":  "https://api.va.gov/oauth2/claims/v1/authorization",
        "token": "https://api.va.gov/oauth2/claims/v1/token",
    },
    "sandbox": {
        "auth":  "https://sandbox-api.va.gov/oauth2/claims/v1/authorization",
        "token": "https://sandbox-api.va.gov/oauth2/claims/v1/token",
    },
}


def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


class TokenStore:
    def __init__(self, token_file: str = TOKEN_FILE):
        self.token_file = token_file

    def load(self) -> dict:
        if os.path.exists(self.token_file):
            with open(self.token_file) as f:
                return json.load(f)
        return {}

    def save(self, tokens: dict) -> None:
        with open(self.token_file, "w") as f:
            json.dump(tokens, f, indent=2)
        os.chmod(self.token_file, 0o600)

    def clear(self) -> None:
        if os.path.exists(self.token_file):
            os.remove(self.token_file)

    def is_valid(self) -> bool:
        tokens = self.load()
        if not tokens.get("access_token"):
            return False
        return time.time() < tokens.get("expires_at", 0) - 60


class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    error = None

    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            _CallbackHandler.auth_code = params["code"][0]
            body = b"<h1>Authentication successful. You can close this window.</h1>"
        else:
            _CallbackHandler.error = params.get("error", ["unknown"])[0]
            body = b"<h1>Authentication failed. Check the terminal for details.</h1>"
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


class OAuthClient:
    def __init__(self, client_id: str, client_secret: str, environment: str = "sandbox"):
        self.client_id = resolve_secret(client_id, "VA_CLIENT_ID") or REAL_CLIENT_ID
        self.client_secret = resolve_secret(client_secret, "VA_CLIENT_SECRET")
        self.pkce = not self.client_secret  # use PKCE when no client_secret is available
        self.endpoints = ENDPOINTS.get(environment, ENDPOINTS["sandbox"])
        self.store = TokenStore()
        self._pkce_verifier: Optional[str] = None

    def get_access_token(self) -> str:
        if self.store.is_valid():
            return self.store.load()["access_token"]

        tokens = self.store.load()
        if tokens.get("refresh_token"):
            try:
                return self._refresh(tokens["refresh_token"])
            except requests.HTTPError:
                pass

        return self._authorize()

    def _authorize(self) -> str:
        _CallbackHandler.auth_code = None
        _CallbackHandler.error = None

        params = {
            "client_id": self.client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPES,
        }

        if self.pkce:
            self._pkce_verifier, challenge = _pkce_pair()
            params["code_challenge"] = challenge
            params["code_challenge_method"] = "S256"

        auth_url = f"{self.endpoints['auth']}?{urlencode(params)}"
        print(f"Opening browser for VA authentication...\nIf it doesn't open, visit:\n{auth_url}\n")
        webbrowser.open(auth_url)

        server = HTTPServer(("localhost", 8080), _CallbackHandler)
        server.handle_request()

        if _CallbackHandler.error:
            raise RuntimeError(f"VA authorization failed: {_CallbackHandler.error}")
        if not _CallbackHandler.auth_code:
            raise RuntimeError("VA authorization failed: no code received.")

        return self._exchange_code(_CallbackHandler.auth_code)

    def _exchange_code(self, code: str) -> str:
        data: dict = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": self.client_id,
        }
        if self.pkce and self._pkce_verifier:
            data["code_verifier"] = self._pkce_verifier
        else:
            data["client_secret"] = self.client_secret

        resp = requests.post(self.endpoints["token"], data=data)
        resp.raise_for_status()
        return self._save(resp.json())

    def _refresh(self, refresh_token: str) -> str:
        data: dict = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": self.client_id,
        }
        if not self.pkce:
            data["client_secret"] = self.client_secret

        resp = requests.post(self.endpoints["token"], data=data)
        resp.raise_for_status()
        return self._save(resp.json())

    def _save(self, token_data: dict) -> str:
        token_data["expires_at"] = time.time() + token_data.get("expires_in", 3600)
        self.store.save(token_data)
        return token_data["access_token"]

    def logout(self) -> None:
        self.store.clear()
        print("Logged out. Token file removed.")
