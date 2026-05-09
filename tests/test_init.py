import json
import sys
import pytest
from unittest.mock import patch, MagicMock, call

import init as init_module
from init import (
    ask, choose, banner, ok, info,
    step_mode, step_auth, step_claim_ids,
    step_notifications, step_write_config,
    step_test, main,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

def make_inputs(*values):
    """Return a side_effect function that yields values in order."""
    it = iter(values)
    return lambda _: next(it)


COOKIE_KEYS = [
    "_ga", "_ga_CSLL4ZEK4L", "_ga_YPB3FD0PQ9",
    "TS01f27c67", "TS0189a5f9", "TS014c0a39",
    "api_session", "CERNER_ELIGIBLE", "vagov_saml_request_prod",
]


# ── TestAsk ───────────────────────────────────────────────────────────────────

class TestAsk:
    def test_returns_typed_value(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "my-value")
        assert ask("Prompt") == "my-value"

    def test_strips_whitespace(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "  trimmed  ")
        assert ask("Prompt") == "trimmed"

    def test_returns_default_on_empty_input(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert ask("Prompt", default="fallback") == "fallback"

    def test_returns_default_on_whitespace_input(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "   ")
        assert ask("Prompt", default="fallback") == "fallback"

    def test_retries_when_required_and_empty(self, monkeypatch, capsys):
        inputs = make_inputs("", "", "final")
        monkeypatch.setattr("builtins.input", inputs)
        result = ask("Required field")
        assert result == "final"
        assert "required" in capsys.readouterr().out.lower()

    def test_prompt_shows_default(self, monkeypatch):
        captured = {}
        def fake_input(p):
            captured["prompt"] = p
            return ""
        monkeypatch.setattr("builtins.input", fake_input)
        ask("MyField", default="mydefault")
        assert "mydefault" in captured["prompt"]

    def test_secret_uses_getpass(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: pytest.fail("input() should not be called"))
        monkeypatch.setattr("getpass.getpass", lambda _: "secret-value")
        assert ask("Password", secret=True) == "secret-value"

    def test_non_secret_uses_input(self, monkeypatch):
        monkeypatch.setattr("getpass.getpass", lambda _: pytest.fail("getpass() should not be called"))
        monkeypatch.setattr("builtins.input", lambda _: "plain-value")
        assert ask("Field") == "plain-value"


# ── TestChoose ────────────────────────────────────────────────────────────────

class TestChoose:
    OPTIONS = [("alpha", "First"), ("beta", "Second"), ("gamma", "Third")]

    def test_returns_first_option_label(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        assert choose("Pick one:", self.OPTIONS) == "alpha"

    def test_returns_last_option_label(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "3")
        assert choose("Pick one:", self.OPTIONS) == "gamma"

    def test_returns_middle_option_label(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "2")
        assert choose("Pick one:", self.OPTIONS) == "beta"

    def test_retries_on_invalid_number(self, monkeypatch, capsys):
        inputs = make_inputs("9", "1")
        monkeypatch.setattr("builtins.input", inputs)
        result = choose("Pick:", self.OPTIONS)
        assert result == "alpha"
        assert "Please enter" in capsys.readouterr().out

    def test_retries_on_non_numeric(self, monkeypatch, capsys):
        inputs = make_inputs("abc", "2")
        monkeypatch.setattr("builtins.input", inputs)
        result = choose("Pick:", self.OPTIONS)
        assert result == "beta"

    def test_retries_on_zero(self, monkeypatch):
        inputs = make_inputs("0", "1")
        monkeypatch.setattr("builtins.input", inputs)
        assert choose("Pick:", self.OPTIONS) == "alpha"

    def test_prints_all_options(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        choose("Pick:", self.OPTIONS)
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "beta" in out
        assert "gamma" in out


# ── TestOutputHelpers ─────────────────────────────────────────────────────────

class TestOutputHelpers:
    def test_banner_contains_text(self, capsys):
        banner("Hello Banner")
        assert "Hello Banner" in capsys.readouterr().out

    def test_ok_contains_checkmark_and_text(self, capsys):
        ok("All good")
        out = capsys.readouterr().out
        assert "✓" in out
        assert "All good" in out

    def test_info_contains_arrow_and_text(self, capsys):
        info("Some info")
        out = capsys.readouterr().out
        assert "→" in out
        assert "Some info" in out


# ── TestStepMode ──────────────────────────────────────────────────────────────

class TestStepMode:
    def test_returns_mock(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        assert step_mode() == "mock"

    def test_returns_sandbox(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "2")
        assert step_mode() == "sandbox"

    def test_returns_real(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "3")
        assert step_mode() == "real"

    def test_retries_on_invalid(self, monkeypatch):
        inputs = make_inputs("0", "5", "abc", "2")
        monkeypatch.setattr("builtins.input", inputs)
        assert step_mode() == "sandbox"


# ── TestStepAuth ──────────────────────────────────────────────────────────────

class TestStepAuth:
    def test_mock_mode_returns_none_auth(self):
        method, oauth, cookies = step_auth("mock")
        assert method == "none"

    def test_mock_mode_returns_empty_oauth(self):
        _, oauth, _ = step_auth("mock")
        assert oauth == {}

    def test_mock_mode_returns_empty_cookies(self):
        _, _, cookies = step_auth("mock")
        assert cookies == {}

    def test_oauth_returns_oauth_method(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("1", "my-client-id"))
        monkeypatch.setattr("getpass.getpass", lambda _: "my-secret")
        method, _, _ = step_auth("sandbox")
        assert method == "oauth"

    def test_oauth_collects_client_id(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("1", "my-client-id"))
        monkeypatch.setattr("getpass.getpass", lambda _: "my-secret")
        _, oauth, _ = step_auth("sandbox")
        assert oauth["client_id"] == "my-client-id"

    def test_oauth_collects_client_secret(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("1", "my-client-id"))
        monkeypatch.setattr("getpass.getpass", lambda _: "my-secret")
        _, oauth, _ = step_auth("sandbox")
        assert oauth["client_secret"] == "my-secret"

    def test_oauth_cookies_are_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("1", "cid"))
        monkeypatch.setattr("getpass.getpass", lambda _: "csec")
        _, _, cookies = step_auth("real")
        assert all(v == "" for v in cookies.values())

    def test_cookies_method_returns_cookies(self, monkeypatch):
        # option 2 = cookies; then 9 cookie values
        cookie_values = ["val" + str(i) for i in range(9)]
        monkeypatch.setattr("builtins.input", make_inputs("2", *cookie_values))
        method, _, cookies = step_auth("real")
        assert method == "cookies"

    def test_cookies_collects_all_nine_keys(self, monkeypatch):
        cookie_values = [f"v{i}" for i in range(9)]
        monkeypatch.setattr("builtins.input", make_inputs("2", *cookie_values))
        _, _, cookies = step_auth("sandbox")
        assert set(cookies.keys()) == set(COOKIE_KEYS)

    def test_cookies_stores_provided_values(self, monkeypatch):
        values = [f"cookie-val-{i}" for i in range(9)]
        monkeypatch.setattr("builtins.input", make_inputs("2", *values))
        _, _, cookies = step_auth("sandbox")
        assert list(cookies.values()) == values

    def test_cookies_oauth_cfg_is_empty(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("2", *["" for _ in range(9)]))
        _, oauth, _ = step_auth("sandbox")
        assert oauth["client_id"] == ""
        assert oauth["client_secret"] == ""

    def test_prints_developer_portal_url(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", make_inputs("1", "cid"))
        monkeypatch.setattr("getpass.getpass", lambda _: "csec")
        step_auth("sandbox")
        assert "developer.va.gov" in capsys.readouterr().out


# ── TestStepClaimIds ──────────────────────────────────────────────────────────

class TestStepClaimIds:
    def test_single_id_returns_string(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "123456")
        result = step_claim_ids()
        assert result == "123456"
        assert isinstance(result, str)

    def test_default_returns_117877436(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        assert step_claim_ids() == "117877436"

    def test_multiple_ids_returns_list(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "111, 222, 333")
        result = step_claim_ids()
        assert result == ["111", "222", "333"]

    def test_two_ids_returns_list(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "111,222")
        result = step_claim_ids()
        assert isinstance(result, list)
        assert len(result) == 2

    def test_strips_whitespace_from_ids(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: " 111 , 222 ")
        result = step_claim_ids()
        assert result == ["111", "222"]

    def test_ignores_empty_segments(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "111,,222")
        result = step_claim_ids()
        assert result == ["111", "222"]


# ── TestStepNotifications ─────────────────────────────────────────────────────

class TestStepNotifications:
    def test_none_send_email_false(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        send_email, _, _ = step_notifications()
        assert send_email is False

    def test_none_push_disabled(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "1")
        _, _, push = step_notifications()
        assert push["enabled"] is False

    def test_email_sets_send_email_true(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "from@t.com", "to@t.com", "smtp.gmail.com", "587", "from@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        send_email, _, _ = step_notifications()
        assert send_email is True

    def test_email_collects_sender(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "from@test.com", "to@t.com", "smtp.gmail.com", "587", "from@test.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        _, email, _ = step_notifications()
        assert email["sender"] == "from@test.com"

    def test_email_collects_receiver(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "from@t.com", "to@test.com", "smtp.gmail.com", "587", "from@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        _, email, _ = step_notifications()
        assert email["receiver"] == "to@test.com"

    def test_email_default_smtp_server(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "f@t.com", "t@t.com", "", "587", "f@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        _, email, _ = step_notifications()
        assert email["smtp_server"] == "smtp.gmail.com"

    def test_email_default_port_587(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "f@t.com", "t@t.com", "smtp.gmail.com", "", "f@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        _, email, _ = step_notifications()
        assert email["smtp_port"] == 587

    def test_email_custom_port(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "f@t.com", "t@t.com", "smtp.t.com", "465", "f@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "pass")
        _, email, _ = step_notifications()
        assert email["smtp_port"] == 465

    def test_email_collects_password_via_getpass(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs(
            "2", "f@t.com", "t@t.com", "smtp.gmail.com", "587", "f@t.com"
        ))
        monkeypatch.setattr("getpass.getpass", lambda _: "secret-pass")
        _, email, _ = step_notifications()
        assert email["password"] == "secret-pass"

    def test_ntfy_enables_push(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("3", "my-topic", ""))
        _, _, push = step_notifications()
        assert push["enabled"] is True
        assert push["provider"] == "ntfy"

    def test_ntfy_collects_topic(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("3", "my-custom-topic", ""))
        _, _, push = step_notifications()
        assert push["topic"] == "my-custom-topic"

    def test_ntfy_default_topic(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("3", "", ""))
        _, _, push = step_notifications()
        assert push["topic"] == "va-claim-checker"

    def test_ntfy_optional_token(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("3", "topic", "my-token"))
        _, _, push = step_notifications()
        assert push["token"] == "my-token"

    def test_ntfy_no_token_when_blank(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("3", "topic", ""))
        _, _, push = step_notifications()
        assert push["token"] == ""

    def test_pushover_enables_push(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("4", "app-tok", "usr-key"))
        _, _, push = step_notifications()
        assert push["enabled"] is True
        assert push["provider"] == "pushover"

    def test_pushover_collects_app_token(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("4", "my-app-token", "usr-key"))
        _, _, push = step_notifications()
        assert push["app_token"] == "my-app-token"

    def test_pushover_collects_user_key(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("4", "app-tok", "my-user-key"))
        _, _, push = step_notifications()
        assert push["user_key"] == "my-user-key"

    def test_pushover_send_email_false(self, monkeypatch):
        monkeypatch.setattr("builtins.input", make_inputs("4", "tok", "key"))
        send_email, _, _ = step_notifications()
        assert send_email is False


# ── TestStepWriteConfig ───────────────────────────────────────────────────────

WRITE_ARGS = dict(
    mode="mock", environment="sandbox", auth_method="none",
    oauth_cfg={"client_id": "", "client_secret": ""},
    cookies={k: "" for k in COOKIE_KEYS},
    claim_id="117877436", send_email=False,
    email_cfg={"sender": "", "receiver": "", "smtp_server": "",
               "smtp_port": 587, "username": "", "password": ""},
    push_cfg={"enabled": False, "provider": "ntfy", "topic": "va-claim-checker", "token": ""},
)


class TestStepWriteConfig:
    def test_creates_config_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        assert (tmp_path / "config.json").exists()

    def test_config_is_valid_json(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert isinstance(data, dict)

    def test_config_contains_mode(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["mode"] == "mock"

    def test_config_contains_environment(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["environment"] == "sandbox"

    def test_config_contains_claim_id(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["claim_id"] == "117877436"

    def test_config_contains_oauth_block(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert "oauth" in data

    def test_config_contains_state_file(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["state_file"] == ".va_state.json"

    def test_skips_when_overwrite_declined(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text('{"mode":"old"}')
        monkeypatch.setattr("builtins.input", lambda _: "n")
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["mode"] == "old"

    def test_overwrites_when_confirmed(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "config.json").write_text('{"mode":"old"}')
        monkeypatch.setattr("builtins.input", lambda _: "y")
        step_write_config(**WRITE_ARGS)
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["mode"] == "mock"

    def test_oauth_info_shown_for_real_oauth(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        step_write_config(**{**WRITE_ARGS, "mode": "real", "environment": "real",
                             "auth_method": "oauth"})
        assert "browser" in capsys.readouterr().out.lower()

    def test_no_oauth_info_for_mock(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        step_write_config(**WRITE_ARGS)
        assert "browser" not in capsys.readouterr().out.lower()

    def test_list_claim_id_written_correctly(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        step_write_config(**{**WRITE_ARGS, "claim_id": ["111", "222"]})
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["claim_id"] == ["111", "222"]


# ── TestStepTest ──────────────────────────────────────────────────────────────

class TestStepTest:
    def test_runs_cli_on_yes(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            step_test("mock")
        mock_run.assert_called_once()

    def test_runs_cli_on_empty_input(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "")
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            step_test("mock")
        mock_run.assert_called_once()

    def test_skips_on_no(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "n")
        with patch("subprocess.run") as mock_run:
            step_test("mock")
        mock_run.assert_not_called()
        assert "Skipped" in capsys.readouterr().out

    def test_cli_called_with_status_subcommand(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        with patch("subprocess.run", return_value=MagicMock(returncode=0)) as mock_run:
            step_test("mock")
        args = mock_run.call_args[0][0]
        assert "cli.py" in args
        assert "status" in args

    def test_success_message_shown_for_real_mode(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            step_test("real")
        assert "successful" in capsys.readouterr().out.lower()

    def test_no_success_message_for_mock(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: "y")
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            step_test("mock")
        assert "successful" not in capsys.readouterr().out.lower()


# ── TestMain ──────────────────────────────────────────────────────────────────

class TestMain:
    def _mock_mode_inputs(self):
        """Inputs for a complete mock-mode run: mode=1, claim=default, notif=none, skip test."""
        return make_inputs("1", "", "1", "n")

    def test_keyboard_interrupt_exits_cleanly(self, monkeypatch):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 0

    def test_keyboard_interrupt_prints_cancelled(self, monkeypatch, capsys):
        monkeypatch.setattr("builtins.input", lambda _: (_ for _ in ()).throw(KeyboardInterrupt))
        with pytest.raises(SystemExit):
            main()
        assert "cancelled" in capsys.readouterr().out.lower()

    def test_full_mock_flow_writes_config(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", self._mock_mode_inputs())
        main()
        assert (tmp_path / "config.json").exists()

    def test_full_mock_flow_config_mode_is_mock(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", self._mock_mode_inputs())
        main()
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["mode"] == "mock"

    def test_sandbox_mode_sets_sandbox_environment(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        # mode=sandbox, auth=oauth, cid, csec, claim=default, notif=none, skip test
        monkeypatch.setattr("builtins.input", make_inputs("2", "1", "my-cid", "", "1", "n"))
        monkeypatch.setattr("getpass.getpass", lambda _: "my-secret")
        main()
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["environment"] == "sandbox"

    def test_real_mode_sets_real_environment(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", make_inputs("3", "1", "my-cid", "", "1", "n"))
        monkeypatch.setattr("getpass.getpass", lambda _: "my-secret")
        main()
        data = json.loads((tmp_path / "config.json").read_text())
        assert data["environment"] == "real"

    def test_prints_setup_complete(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", self._mock_mode_inputs())
        main()
        assert "Setup complete" in capsys.readouterr().out

    def test_prints_useful_commands(self, monkeypatch, tmp_path, capsys):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr("builtins.input", self._mock_mode_inputs())
        main()
        out = capsys.readouterr().out
        assert "cli.py status" in out
        assert "cli.py check" in out
