"""
Normalizes VA Lighthouse API v2 claim responses into a flat dict
that the rest of the app consumes.

Real response shape (v2):
{
  "data": {
    "id": "600236068",
    "type": "claim",
    "attributes": {
      "claimDate": "2023-05-11",
      "claimType": "Compensation",
      "claimTypeCode": "110LCMP7IDES",
      "claimPhaseDates": {
        "latestPhaseType": "Pending Decision Approval",
        "phaseChangeDate": "2023-11-08",
        "currentPhaseBack": false,
        "phase1CompleteDate": "...",
        ...
      },
      "status": "PENDING",
      "closeDate": null,
      "estimatedDecisionDate": "2024-03-15",
      "contentions": [{"name": "Tinnitus"}],
      "decisionLetterSent": false,
      "documentsNeeded": false,
      "developmentLetterSent": false
    }
  }
}
"""

from typing import Any, Dict


def normalize(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Return a flat, normalized claim dict regardless of API version."""

    # Already normalized (mock data or previously parsed)
    if "claim_id" in raw:
        return raw

    data = raw.get("data", raw)
    attrs = data.get("attributes", data)
    phase_dates = attrs.get("claimPhaseDates", {})

    contentions = attrs.get("contentions", [])
    contention_names = ", ".join(c.get("name", "") for c in contentions) or "None listed"

    return {
        "claim_id": data.get("id", attrs.get("claimId", "unknown")),
        "status": attrs.get("status", attrs.get("claimStatus", "Unknown")),
        "claim_type": attrs.get("claimType", "Unknown"),
        "claim_date": attrs.get("claimDate", "unknown"),
        "stage": phase_dates.get("latestPhaseType", attrs.get("stage", "Unknown")),
        "last_updated": phase_dates.get("phaseChangeDate", attrs.get("last_updated", "unknown")),
        "phase_went_back": phase_dates.get("currentPhaseBack", False),
        "estimated_decision_date": attrs.get("estimatedDecisionDate"),
        "close_date": attrs.get("closeDate"),
        "decision_letter_sent": attrs.get("decisionLetterSent", False),
        "documents_needed": attrs.get("documentsNeeded", False),
        "contentions": contention_names,
        "details": attrs.get("details", "No details available."),
    }
