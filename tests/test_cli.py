import json
import sys
import pytest
from unittest.mock import patch

from cli import main


def run(args, config_file):
    with patch("sys.argv", ["cli.py", "--config", config_file] + args):
        main()


class TestStatusCommand:
    def test_prints_claim_id(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["status"], path)
        assert "117877436" in capsys.readouterr().out

    def test_prints_status_field(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["status"], path)
        assert "Pending" in capsys.readouterr().out

    def test_accepts_claim_id_override(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["status", "--claim-id", "default"], path)
        assert "default" in capsys.readouterr().out


class TestCheckCommand:
    def test_notifies_on_first_run(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["check"], path)
        out = capsys.readouterr().out
        assert "Change detected" in out or "mock notification" in out.lower()

    def test_silent_on_second_run(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["check"], path)
        capsys.readouterr()
        run(["check"], path)
        assert "No change" in capsys.readouterr().out

    def test_accepts_multiple_claim_ids(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["check", "--claim-id", "117877436", "default"], path)
        out = capsys.readouterr().out
        assert "117877436" in out
        assert "default" in out


class TestClaimsCommand:
    def test_lists_known_claim(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["claims"], path)
        assert "117877436" in capsys.readouterr().out

    def test_output_has_status(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["claims"], path)
        assert "Pending" in capsys.readouterr().out

    def test_output_has_stage(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["claims"], path)
        assert "Evidence Gathering" in capsys.readouterr().out


class TestResetCommand:
    def test_reset_all_prints_confirmation(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["reset"], path)
        assert "reset" in capsys.readouterr().out.lower()

    def test_reset_specific_claim_prints_id(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["check"], path)
        capsys.readouterr()
        run(["reset", "--claim-id", "117877436"], path)
        assert "117877436" in capsys.readouterr().out

    def test_reset_clears_state(self, tmp_config, capsys):
        path, cfg, tmp_path = tmp_config
        from state import StateStore
        run(["check"], path)
        capsys.readouterr()
        run(["reset"], path)
        capsys.readouterr()
        store = StateStore(cfg["state_file"])
        assert store.get("117877436") is None

    def test_reset_then_check_notifies_again(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["check"], path)
        run(["reset"], path)
        capsys.readouterr()
        run(["check"], path)
        out = capsys.readouterr().out
        assert "Change detected" in out or "mock notification" in out.lower()


class TestLogoutCommand:
    def test_logout_without_oauth_prints_message(self, tmp_config, capsys):
        path, _, _ = tmp_config
        run(["logout"], path)
        assert "not configured" in capsys.readouterr().out.lower()

    def test_logout_with_oauth_calls_logout(self, tmp_config, capsys, tmp_path):
        path, cfg, _ = tmp_config
        new_cfg = {**cfg, "oauth": {"client_id": "real-id", "client_secret": "real-secret"}}
        new_path = str(tmp_path / "cfg2.json")
        with open(new_path, "w") as f:
            json.dump(new_cfg, f)
        with patch("auth.OAuthClient.logout") as mock_logout:
            run(["logout"], new_path)
        mock_logout.assert_called_once()


class TestWatchCommand:
    def test_watch_calls_run_check_then_sleeps(self, tmp_config, capsys):
        path, _, _ = tmp_config
        call_count = {"n": 0}

        def fake_sleep(seconds):
            call_count["n"] += 1
            if call_count["n"] >= 2:
                raise KeyboardInterrupt

        with patch("time.sleep", side_effect=fake_sleep):
            with pytest.raises((KeyboardInterrupt, SystemExit)):
                run(["watch", "--interval", "5"], path)

        assert call_count["n"] >= 1


class TestHelpOutput:
    def test_check_in_subcommands(self, tmp_config, capsys):
        path, _, _ = tmp_config
        with pytest.raises(SystemExit):
            run(["--help"], path)
        assert "check" in capsys.readouterr().out

    def test_all_subcommands_listed(self, tmp_config, capsys):
        path, _, _ = tmp_config
        with pytest.raises(SystemExit):
            run(["--help"], path)
        out = capsys.readouterr().out
        for cmd in ("check", "status", "claims", "reset", "watch", "logout"):
            assert cmd in out
