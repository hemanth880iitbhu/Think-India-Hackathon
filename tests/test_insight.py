"""
Validation tests for rule_based_insight().

Run standalone:   python tests/test_insight.py
Run with pytest:  python -m pytest tests/test_insight.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ai_pipeline import rule_based_insight


PLACEHOLDER_STRINGS = {
    "See SOAP note.",
    "See SOAP note",
    "Imported",
    "Awaiting AI analysis of first visit...",
}


def _assert_no_placeholders(insight):
    for field in ("assessment", "rationale"):
        val = insight.get(field, "")
        assert val not in PLACEHOLDER_STRINGS, (
            f"Placeholder text found in field '{field}': {val!r}"
        )
    for rec in insight.get("recommendation") or []:
        assert rec not in PLACEHOLDER_STRINGS, (
            f"Placeholder text found in recommendation: {rec!r}"
        )






def test_canonical_upper_abdominal_pain():
    """
    Canonical sample: upper abdominal pain + nausea + no fever +
    stable vitals + tenderness.
    Should produce a useful clinical insight and NOT be High risk.
    """
    note = (
        "मरीज को 2 दिन से पेट के ऊपरी हिस्से में तेज दर्द (Abdominal Pain) है। "
        "साथ में हल्की जी मिचलाने (Nausea) की शिकायत है। No fever. "
        "Vitals: BP 120/80, Pulse 72. "
        "पेट छूने पर दर्द बढ़ रहा है (Tenderness present). "
        "Prescribed Antacid and advised liquid diet."
    )
    insight = rule_based_insight(note)

    _assert_no_placeholders(insight)
    assert insight["risk_level"] in ("Low", "Medium"), (
        f"Expected Low or Medium risk, got {insight['risk_level']}"
    )
    assert isinstance(insight["red_flags"], list)
    assert len(insight["recommendation"]) >= 1
    assert insight["assessment"] != ""

    assert (
        "afebrile" in insight["rationale"].lower()
        or "stable" in insight["rationale"].lower()
    ), f"Expected rationale to mention afebrile/stable, got: {insight['rationale']}"


def test_empty_notes_returns_safe_message():
    """Empty notes → safe fallback, never a placeholder."""
    insight = rule_based_insight("")
    _assert_no_placeholders(insight)
    assert insight["assessment"] == "Insufficient data to generate insight."
    assert insight["risk_level"] == "Low"


def test_none_notes_returns_safe_message():
    """None notes → safe fallback."""
    insight = rule_based_insight(None)
    _assert_no_placeholders(insight)
    assert insight["assessment"] == "Insufficient data to generate insight."


def test_whitespace_only_notes_returns_safe_message():
    """Whitespace-only notes → safe fallback."""
    insight = rule_based_insight("   \n  ")
    _assert_no_placeholders(insight)
    assert insight["assessment"] == "Insufficient data to generate insight."


def test_chest_pain_triggers_high_risk():
    """Chest pain should trigger High risk with relevant red flag."""
    note = "Patient has severe chest pain and breathlessness. BP 90/60."
    insight = rule_based_insight(note)
    _assert_no_placeholders(insight)
    assert insight["risk_level"] == "High"
    assert len(insight["red_flags"]) > 0


def test_stable_gastritis_is_low_or_medium():
    """Simple gastritis without red flags → Low or Medium risk."""
    note = "Gastritis. Patient has stomach pain. No fever. BP 118/78. Antacid prescribed."
    insight = rule_based_insight(note)
    _assert_no_placeholders(insight)
    assert insight["risk_level"] in ("Low", "Medium")


def test_entities_diagnoses_used_in_assessment():
    """Entities with diagnoses should appear in assessment when no LLM summary."""
    note = "Patient complaint of headache."
    entities = {"symptoms": ["Headache"], "diagnoses": ["Tension headache"]}
    insight = rule_based_insight(note, entities=entities)
    _assert_no_placeholders(insight)
    assert "Tension headache" in insight["assessment"]


def test_clinical_summary_preferred_over_rules():
    """A valid clinical_summary from the LLM should be used as the assessment."""
    note = "Fever and cough for 3 days."
    clinical_summary = "Acute viral upper respiratory infection with stable vitals."
    insight = rule_based_insight(note, clinical_summary=clinical_summary)
    _assert_no_placeholders(insight)
    assert insight["assessment"] == clinical_summary


def test_hypertensive_bp_flagged():
    """Hypertensive BP should appear in red_flags and trigger High risk."""
    note = "Patient presents with headache. BP 170/105, Pulse 80. No other complaints."
    insight = rule_based_insight(note)
    _assert_no_placeholders(insight)
    assert insight["risk_level"] == "High"
    assert any(
        "hypertensive" in f.lower() or "bp" in f.lower()
        for f in insight["red_flags"]
    )


def test_hindi_only_note_parsed():
    """Pure Hindi note should not crash and should not emit placeholders."""
    note = "मरीज को बुखार है। पेट में दर्द और उल्टी है। BP 130/85."
    insight = rule_based_insight(note)
    _assert_no_placeholders(insight)
    assert insight["risk_level"] in ("Low", "Medium", "High")
    assert isinstance(insight["recommendation"], list)


def test_antacid_in_recommendation():
    """Antacid in note should produce a follow-up recommendation for antacid."""
    note = "Epigastric pain, no fever. BP 122/80. Omeprazole prescribed."
    insight = rule_based_insight(note)
    _assert_no_placeholders(insight)
    rec_text = " ".join(insight["recommendation"]).lower()
    assert "antacid" in rec_text or "reassess" in rec_text or "monitor" in rec_text


def test_all_required_fields_present():
    """Returned dict must always have all required fields."""
    note = "Routine check-up. No complaints."
    insight = rule_based_insight(note)
    for field in ("assessment", "risk_level", "red_flags", "recommendation", "rationale"):
        assert field in insight, f"Missing field: {field}"
    assert insight["risk_level"] in ("Low", "Medium", "High")
    assert isinstance(insight["red_flags"], list)
    assert isinstance(insight["recommendation"], list)






if __name__ == "__main__":
    tests = [
        test_canonical_upper_abdominal_pain,
        test_empty_notes_returns_safe_message,
        test_none_notes_returns_safe_message,
        test_whitespace_only_notes_returns_safe_message,
        test_chest_pain_triggers_high_risk,
        test_stable_gastritis_is_low_or_medium,
        test_entities_diagnoses_used_in_assessment,
        test_clinical_summary_preferred_over_rules,
        test_hypertensive_bp_flagged,
        test_hindi_only_note_parsed,
        test_antacid_in_recommendation,
        test_all_required_fields_present,
    ]

    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1

    print(f"\n{passed}/{passed + failed} tests passed.")
    if failed:
        sys.exit(1)
