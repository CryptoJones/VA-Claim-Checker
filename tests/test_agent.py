import json
import pytest
from unittest.mock import patch, MagicMock

from agent import VAClaimAgent


@pytest.fixture
def agent(tmp_config):
    path, _, _ = tmp_config
    return VAClaimAgent(config_file=path)


class TestLoadConfig:
    def test_loads_from_file(self, tmp_config):
        path, cfg, _ = tmp_config
        a = VAClaimAgent(config_file=path)
        assert a.config["mode"] == "mock"
        assert a.config["claim_id"] == "117877436"

    def test_returns_defaults_when_file_missing(self, tmp_path):
        a = VAClaimAgent(config_file=str(tmp_path / "nope.json"))
        assert a.config["mode"] == "mock"
        assert "claim_id" in a.config
        assert "email" in a.config

    def test_environment_loaded(self, tmp_config):
        path, _, _ = tmp_config
        a = VAClaimAgent(config_file=path)
        assert a.config["environment"] == "sandbox"

    def test_state_file_from_config(self, tmp_config):
        path, cfg, _ = tmp_config
        a = VAClaimAgent(config_file=path)
        assert a.state.state_file == cfg["state_file"]


class TestAnalyzeStatus:
    def test_includes_claim_id(self, agent, base_claim):
        assert "117877436" in agent.analyze_status(base_claim)

    def test_includes_status(self, agent, base_claim):
        assert "Pending" in agent.analyze_status(base_claim)

    def test_includes_stage(self, agent, base_claim):
        assert "Evidence Gathering" in agent.analyze_status(base_claim)

    def test_includes_last_updated(self, agent, base_claim):
        assert "2026-05-01" in agent.analyze_status(base_claim)

    def test_estimated_decision_date_shown_when_present(self, agent, base_claim):
        claim = {**base_claim, "estimated_decision_date": "2026-06-15"}
        assert "2026-06-15" in agent.analyze_status(claim)

    def test_estimated_decision_date_absent_when_none(self, agent, base_claim):
        result = agent.analyze_status(base_claim)
        assert "Est. decision" not in result

    def test_decision_letter_shown_when_sent(self, agent, base_claim):
        claim = {**base_claim, "decision_letter_sent": True}
        assert "Decision letter" in agent.analyze_status(claim)

    def test_documents_needed_shown(self, agent, base_claim):
        claim = {**base_claim, "documents_needed": True}
        assert "Action required" in agent.analyze_status(claim)

    def test_phase_went_back_shown(self, agent, base_claim):
        claim = {**base_claim, "phase_went_back": True}
        assert "previous phase" in agent.analyze_status(claim)

    def test_contentions_shown_when_present(self, agent, base_claim):
        claim = {**base_claim, "contentions": "Tinnitus, PTSD"}
        assert "Tinnitus, PTSD" in agent.analyze_status(claim)

    def test_contentions_hidden_when_none_listed(self, agent, base_claim):
        result = agent.analyze_status(base_claim)
        assert "Contentions" not in result


class TestRunCheck:
    def test_notifies_on_first_run(self, agent):
        with patch.object(agent.notifier, "notify") as mock_notify:
            agent.run_check()
        mock_notify.assert_called_once()

    def test_silent_on_second_run_no_change(self, agent):
        agent.run_check()
        with patch.object(agent.notifier, "notify") as mock_notify:
            agent.run_check()
        mock_notify.assert_not_called()

    def test_notifies_again_on_state_change(self, agent):
        agent.run_check()
        agent.state.save("117877436", {
            "status": "COMPLETE", "stage": "Decision Letter Ready",
            "last_updated": "2026-05-09", "estimated_decision_date": None,
        })
        with patch.object(agent.api_client, "get_claim", return_value={
            "claim_id": "117877436", "claim_type": "Compensation",
            "status": "COMPLETE", "stage": "Decision Letter Ready",
            "last_updated": "2026-05-10", "estimated_decision_date": None,
            "decision_letter_sent": True, "documents_needed": False,
            "phase_went_back": False, "contentions": "None listed",
            "details": "",
        }):
            with patch.object(agent.notifier, "notify") as mock_notify:
                agent.run_check()
        mock_notify.assert_called_once()

    def test_saves_state_after_notify(self, agent):
        agent.run_check()
        assert agent.state.get("117877436") is not None

    def test_checks_all_configured_claim_ids(self, tmp_path):
        cfg = {
            "mode": "mock", "environment": "sandbox",
            "claim_id": ["117877436", "default"],
            "send_email": False, "oauth": {"client_id": "", "client_secret": ""},
            "cookies": {}, "push": {"enabled": False},
            "state_file": str(tmp_path / ".va_state.json"),
            "log_file": str(tmp_path / "test.log"),
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(cfg))
        a = VAClaimAgent(config_file=str(path))
        with patch.object(a.notifier, "notify") as mock_notify:
            a.run_check()
        assert mock_notify.call_count == 2

    def test_run_check_with_explicit_claim_ids(self, agent):
        with patch.object(agent.notifier, "notify") as mock_notify:
            agent.run_check(claim_ids=["117877436"])
        mock_notify.assert_called_once()


class TestConfiguredClaimIds:
    def test_single_string_claim_id(self, agent):
        ids = agent._configured_claim_ids()
        assert ids == ["117877436"]

    def test_list_claim_ids(self, tmp_path):
        cfg = {
            "mode": "mock", "environment": "sandbox",
            "claim_id": ["111", "222", "333"],
            "send_email": False, "oauth": {"client_id": "", "client_secret": ""},
            "cookies": {}, "push": {"enabled": False},
            "state_file": str(tmp_path / ".va_state.json"),
            "log_file": str(tmp_path / "test.log"),
        }
        path = tmp_path / "config.json"
        path.write_text(json.dumps(cfg))
        a = VAClaimAgent(config_file=str(path))
        assert a._configured_claim_ids() == ["111", "222", "333"]


class TestFetchClaim:
    def test_returns_normalized_dict(self, agent):
        result = agent.fetch_claim("117877436")
        assert "claim_id" in result
        assert "status" in result
        assert "stage" in result

    def test_uses_configured_id_when_none_given(self, agent):
        result = agent.fetch_claim()
        assert result["claim_id"] == "117877436"


class TestGetClaimAnalysis:
    def test_returns_string(self, agent):
        result = agent.get_claim_analysis("117877436")
        assert isinstance(result, str)

    def test_contains_claim_id(self, agent):
        assert "117877436" in agent.get_claim_analysis("117877436")

    def test_uses_configured_id_when_none_given(self, agent):
        result = agent.get_claim_analysis()
        assert "117877436" in result


class TestListClaims:
    def test_returns_list(self, agent):
        result = agent.list_claims()
        assert isinstance(result, list)

    def test_items_are_normalized(self, agent):
        results = agent.list_claims()
        for item in results:
            assert "claim_id" in item
            assert "status" in item
