import pytest
from va_response_parser import normalize


V2_RESPONSE = {
    "data": {
        "id": "600236068",
        "type": "claim",
        "attributes": {
            "claimDate": "2023-05-11",
            "claimType": "Compensation",
            "status": "PENDING",
            "closeDate": None,
            "estimatedDecisionDate": "2024-03-15",
            "decisionLetterSent": False,
            "documentsNeeded": True,
            "developmentLetterSent": False,
            "contentions": [{"name": "Tinnitus"}, {"name": "PTSD"}],
            "claimPhaseDates": {
                "latestPhaseType": "Pending Decision Approval",
                "phaseChangeDate": "2023-11-08",
                "currentPhaseBack": False,
            },
        },
    }
}


class TestNormalizeAlreadyFlat:
    def test_passthrough_when_claim_id_present(self):
        data = {"claim_id": "123", "status": "Pending", "stage": "Review"}
        assert normalize(data) is data

    def test_mock_data_untouched(self, base_claim):
        result = normalize(base_claim)
        assert result is base_claim


class TestNormalizeV2Response:
    def test_claim_id_extracted(self):
        assert normalize(V2_RESPONSE)["claim_id"] == "600236068"

    def test_status_extracted(self):
        assert normalize(V2_RESPONSE)["status"] == "PENDING"

    def test_claim_type_extracted(self):
        assert normalize(V2_RESPONSE)["claim_type"] == "Compensation"

    def test_stage_from_phase_dates(self):
        assert normalize(V2_RESPONSE)["stage"] == "Pending Decision Approval"

    def test_last_updated_from_phase_change_date(self):
        assert normalize(V2_RESPONSE)["last_updated"] == "2023-11-08"

    def test_estimated_decision_date(self):
        assert normalize(V2_RESPONSE)["estimated_decision_date"] == "2024-03-15"

    def test_documents_needed(self):
        assert normalize(V2_RESPONSE)["documents_needed"] is True

    def test_decision_letter_sent(self):
        assert normalize(V2_RESPONSE)["decision_letter_sent"] is False

    def test_phase_went_back(self):
        assert normalize(V2_RESPONSE)["phase_went_back"] is False

    def test_contentions_joined(self):
        assert normalize(V2_RESPONSE)["contentions"] == "Tinnitus, PTSD"

    def test_claim_date_extracted(self):
        assert normalize(V2_RESPONSE)["claim_date"] == "2023-05-11"


class TestNormalizeMissingFields:
    def test_missing_phase_dates_defaults(self):
        raw = {"data": {"id": "1", "attributes": {"status": "COMPLETE"}}}
        result = normalize(raw)
        assert result["stage"] == "Unknown"
        assert result["last_updated"] == "unknown"
        assert result["phase_went_back"] is False

    def test_missing_estimated_decision_date(self):
        raw = {"data": {"id": "1", "attributes": {}}}
        result = normalize(raw)
        assert result["estimated_decision_date"] is None

    def test_missing_close_date(self):
        raw = {"data": {"id": "1", "attributes": {}}}
        assert normalize(raw)["close_date"] is None

    def test_unknown_claim_id_fallback(self):
        raw = {"data": {"attributes": {}}}
        assert normalize(raw)["claim_id"] == "unknown"


class TestNormalizeContentions:
    def test_empty_contentions(self):
        raw = {"data": {"id": "1", "attributes": {"contentions": []}}}
        assert normalize(raw)["contentions"] == "None listed"

    def test_single_contention(self):
        raw = {"data": {"id": "1", "attributes": {"contentions": [{"name": "Tinnitus"}]}}}
        assert normalize(raw)["contentions"] == "Tinnitus"

    def test_multiple_contentions(self):
        raw = {
            "data": {
                "id": "1",
                "attributes": {
                    "contentions": [
                        {"name": "Tinnitus"},
                        {"name": "PTSD"},
                        {"name": "Back injury"},
                    ]
                },
            }
        }
        assert normalize(raw)["contentions"] == "Tinnitus, PTSD, Back injury"

    def test_missing_contentions_key(self):
        raw = {"data": {"id": "1", "attributes": {}}}
        assert normalize(raw)["contentions"] == "None listed"
