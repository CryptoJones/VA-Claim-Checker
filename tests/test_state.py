import json
import pytest
from state import StateStore


@pytest.fixture
def store(tmp_path):
    return StateStore(str(tmp_path / "state.json"))


@pytest.fixture
def saved_claim():
    return {
        "status": "Pending",
        "stage": "Evidence Gathering",
        "last_updated": "2026-05-01",
        "estimated_decision_date": None,
    }


class TestGet:
    def test_returns_none_for_unknown_claim(self, store):
        assert store.get("999") is None

    def test_returns_saved_claim(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.get("123")
        assert result["status"] == "Pending"
        assert result["stage"] == "Evidence Gathering"

    def test_claim_id_coerced_to_string(self, store, saved_claim):
        store.save(123, saved_claim)
        assert store.get("123") is not None
        assert store.get(123) is not None

    def test_multiple_claims_isolated(self, store, saved_claim):
        store.save("111", saved_claim)
        store.save("222", {**saved_claim, "status": "Complete"})
        assert store.get("111")["status"] == "Pending"
        assert store.get("222")["status"] == "Complete"


class TestSave:
    def test_persists_to_disk(self, store, saved_claim, tmp_path):
        store.save("123", saved_claim)
        assert (tmp_path / "state.json").exists()

    def test_saved_fields(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.get("123")
        assert result["status"] == saved_claim["status"]
        assert result["stage"] == saved_claim["stage"]
        assert result["last_updated"] == saved_claim["last_updated"]
        assert result["estimated_decision_date"] == saved_claim["estimated_decision_date"]

    def test_notified_at_recorded(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.get("123")
        assert "notified_at" in result
        assert result["notified_at"]  # non-empty

    def test_overwrite_existing(self, store, saved_claim):
        store.save("123", saved_claim)
        store.save("123", {**saved_claim, "status": "Complete"})
        assert store.get("123")["status"] == "Complete"

    def test_preserves_other_claims(self, store, saved_claim):
        store.save("111", saved_claim)
        store.save("222", {**saved_claim, "stage": "Rating Decision"})
        assert store.get("111")["stage"] == "Evidence Gathering"


class TestHasChanged:
    def test_true_when_no_prior_state(self, store, saved_claim):
        assert store.has_changed("123", saved_claim) is True

    def test_false_when_same(self, store, saved_claim):
        store.save("123", saved_claim)
        assert store.has_changed("123", saved_claim) is False

    def test_true_when_status_changes(self, store, saved_claim):
        store.save("123", saved_claim)
        assert store.has_changed("123", {**saved_claim, "status": "COMPLETE"}) is True

    def test_true_when_stage_changes(self, store, saved_claim):
        store.save("123", saved_claim)
        assert store.has_changed("123", {**saved_claim, "stage": "Rating Decision"}) is True

    def test_true_when_date_changes(self, store, saved_claim):
        store.save("123", saved_claim)
        assert store.has_changed("123", {**saved_claim, "last_updated": "2026-05-09"}) is True

    def test_false_when_only_estimated_date_changes(self, store, saved_claim):
        store.save("123", saved_claim)
        updated = {**saved_claim, "estimated_decision_date": "2026-06-01"}
        assert store.has_changed("123", updated) is False


class TestDiffSummary:
    def test_first_time_message(self, store, saved_claim):
        result = store.diff_summary("123", saved_claim)
        assert "First time" in result

    def test_no_changes_message(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.diff_summary("123", saved_claim)
        assert "No changes" in result

    def test_status_change_shown(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.diff_summary("123", {**saved_claim, "status": "COMPLETE"})
        assert "Pending" in result
        assert "COMPLETE" in result

    def test_stage_change_shown(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.diff_summary("123", {**saved_claim, "stage": "Rating Decision"})
        assert "Evidence Gathering" in result
        assert "Rating Decision" in result

    def test_date_change_shown(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.diff_summary("123", {**saved_claim, "last_updated": "2026-05-09"})
        assert "2026-05-01" in result
        assert "2026-05-09" in result

    def test_multiple_changes_all_shown(self, store, saved_claim):
        store.save("123", saved_claim)
        result = store.diff_summary("123", {
            **saved_claim,
            "status": "COMPLETE",
            "stage": "Decision Letter Ready",
        })
        assert "Status" in result
        assert "Stage" in result


class TestReset:
    def test_reset_single_claim(self, store, saved_claim):
        store.save("111", saved_claim)
        store.save("222", saved_claim)
        store.reset("111")
        assert store.get("111") is None
        assert store.get("222") is not None

    def test_reset_all_removes_file(self, store, saved_claim, tmp_path):
        store.save("123", saved_claim)
        store.reset()
        assert not (tmp_path / "state.json").exists()

    def test_reset_nonexistent_claim_safe(self, store):
        store.reset("999")  # should not raise

    def test_reset_all_when_no_file(self, store):
        store.reset()  # should not raise
