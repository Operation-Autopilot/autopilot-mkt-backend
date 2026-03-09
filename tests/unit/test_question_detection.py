"""Tests for question detection from chips and message content.

Verifies that both chip-based and content-based detection work,
especially for free-text questions like company_name that have no chips.
"""

from src.services.agent_service import _detect_question_from_chips, _detect_question_from_content


class TestDetectQuestionFromChips:
    def test_exact_chip_match(self):
        assert _detect_question_from_chips(["Vacuum", "Sweep", "Mop", "Other"]) == "method"

    def test_no_chips_returns_none(self):
        assert _detect_question_from_chips(None) is None
        assert _detect_question_from_chips([]) is None

    def test_unrecognized_chips_returns_none(self):
        assert _detect_question_from_chips(["Foo", "Bar"]) is None


class TestDetectQuestionFromContent:
    def test_detects_company_name(self):
        assert _detect_question_from_content("What is the name of your company?") == "company_name"

    def test_detects_company_name_varied_phrasing(self):
        assert _detect_question_from_content("Could you share your company name with me?") == "company_name"

    def test_detects_company_type(self):
        assert _detect_question_from_content("What type of facility do you operate?") == "company_type"

    def test_detects_frequency(self):
        assert _detect_question_from_content("How often do you clean the courts?") == "frequency"

    def test_detects_monthly_spend(self):
        assert _detect_question_from_content("What's your monthly cleaning budget?") == "monthly_spend"

    def test_detects_duration(self):
        assert _detect_question_from_content("How long does each cleaning session take?") == "duration"

    def test_returns_none_for_generic_message(self):
        assert _detect_question_from_content("Thanks for sharing that information!") is None

    def test_returns_none_for_empty(self):
        assert _detect_question_from_content("") is None
        assert _detect_question_from_content(None) is None
