import pytest
from unittest.mock import patch, MagicMock, call

from notifier import Notifier, _resolve


class TestResolve:
    def test_env_var_wins(self, monkeypatch):
        monkeypatch.setenv("VA_SMTP_PASSWORD", "from-env")
        assert _resolve("from-config", "VA_SMTP_PASSWORD") == "from-env"

    def test_falls_back_to_config(self, monkeypatch):
        monkeypatch.delenv("VA_SMTP_PASSWORD", raising=False)
        assert _resolve("from-config", "VA_SMTP_PASSWORD") == "from-config"

    def test_empty_when_nothing_set(self, monkeypatch):
        monkeypatch.delenv("VA_SMTP_PASSWORD", raising=False)
        assert _resolve("", "VA_SMTP_PASSWORD") == ""


class TestNotifyMock:
    def test_prints_when_no_channels_enabled(self, capsys):
        n = Notifier({"send_email": False, "push": {"enabled": False}})
        n.notify("hello world", claim_id="123")
        out = capsys.readouterr().out
        assert "hello world" in out

    def test_prints_mock_label(self, capsys):
        n = Notifier({"send_email": False, "push": {"enabled": False}})
        n.notify("msg")
        assert "mock notification" in capsys.readouterr().out.lower()

    def test_no_print_when_email_enabled(self, capsys):
        n = Notifier({
            "send_email": True,
            "push": {"enabled": False},
            "email": {"sender": "a", "receiver": "b", "smtp_server": "s", "smtp_port": 587,
                      "username": "u", "password": "p"},
        })
        with patch("smtplib.SMTP"):
            n.notify("msg")
        out = capsys.readouterr().out
        assert "mock notification" not in out.lower()


class TestSendEmail:
    @pytest.fixture
    def email_notifier(self):
        return Notifier({
            "send_email": True,
            "push": {"enabled": False},
            "email": {
                "sender": "from@test.com",
                "receiver": "to@test.com",
                "smtp_server": "smtp.test.com",
                "smtp_port": 587,
                "username": "from@test.com",
                "password": "secret",
            },
        })

    def test_smtp_called(self, email_notifier):
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            email_notifier.notify("body", claim_id="123")
        mock_smtp.assert_called_once_with("smtp.test.com", 587)

    def test_starttls_called(self, email_notifier):
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            email_notifier.notify("body")
        ctx.starttls.assert_called_once()

    def test_login_called_with_credentials(self, email_notifier):
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            email_notifier.notify("body")
        ctx.login.assert_called_once_with("from@test.com", "secret")

    def test_send_message_called(self, email_notifier):
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            email_notifier.notify("body")
        ctx.send_message.assert_called_once()

    def test_subject_includes_claim_id(self, email_notifier):
        sent = {}
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            ctx.send_message.side_effect = lambda m: sent.update({"subject": m["Subject"]})
            email_notifier.notify("body", claim_id="999")
        assert "999" in sent["subject"]

    def test_password_from_env_var(self, monkeypatch):
        monkeypatch.setenv("VA_SMTP_PASSWORD", "env-password")
        n = Notifier({
            "send_email": True,
            "push": {"enabled": False},
            "email": {"sender": "a", "receiver": "b", "smtp_server": "s", "smtp_port": 587,
                      "username": "u", "password": "config-password"},
        })
        with patch("smtplib.SMTP") as mock_smtp:
            ctx = MagicMock()
            mock_smtp.return_value.__enter__.return_value = ctx
            n.notify("body")
        ctx.login.assert_called_once_with("u", "env-password")


class TestNtfyPush:
    @pytest.fixture
    def ntfy_notifier(self):
        return Notifier({
            "send_email": False,
            "push": {"enabled": True, "provider": "ntfy", "topic": "va-test", "token": ""},
        })

    def test_posts_to_ntfy(self, ntfy_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            ntfy_notifier.notify("msg", claim_id="123")
        assert mock_post.called
        assert "ntfy.sh/va-test" in mock_post.call_args[0][0]

    def test_title_header_set(self, ntfy_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            ntfy_notifier.notify("msg", claim_id="123")
        headers = mock_post.call_args[1]["headers"]
        assert "Title" in headers

    def test_auth_header_when_token_set(self):
        n = Notifier({
            "send_email": False,
            "push": {"enabled": True, "provider": "ntfy", "topic": "test", "token": "mytoken"},
        })
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            n.notify("msg")
        headers = mock_post.call_args[1]["headers"]
        assert headers.get("Authorization") == "Bearer mytoken"

    def test_no_auth_header_when_no_token(self, ntfy_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            ntfy_notifier.notify("msg")
        headers = mock_post.call_args[1]["headers"]
        assert "Authorization" not in headers


class TestPushoverPush:
    @pytest.fixture
    def pushover_notifier(self):
        return Notifier({
            "send_email": False,
            "push": {
                "enabled": True,
                "provider": "pushover",
                "app_token": "app-tok",
                "user_key": "user-key",
            },
        })

    def test_posts_to_pushover(self, pushover_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            pushover_notifier.notify("msg")
        assert "pushover.net" in mock_post.call_args[0][0]

    def test_sends_token_and_user(self, pushover_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            pushover_notifier.notify("msg")
        data = mock_post.call_args[1]["data"]
        assert data["token"] == "app-tok"
        assert data["user"] == "user-key"

    def test_sends_message_body(self, pushover_notifier):
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            pushover_notifier.notify("hello pushover")
        data = mock_post.call_args[1]["data"]
        assert data["message"] == "hello pushover"

    def test_token_from_env_var(self, monkeypatch):
        monkeypatch.setenv("VA_PUSHOVER_APP_TOKEN", "env-tok")
        n = Notifier({
            "send_email": False,
            "push": {"enabled": True, "provider": "pushover", "app_token": "", "user_key": "uk"},
        })
        with patch("requests.post") as mock_post:
            mock_post.return_value.raise_for_status = MagicMock()
            n.notify("msg")
        assert mock_post.call_args[1]["data"]["token"] == "env-tok"
