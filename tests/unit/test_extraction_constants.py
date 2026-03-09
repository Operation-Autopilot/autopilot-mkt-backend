"""Unit tests for extraction_constants — IDEA-03: Time period context for questions."""

from src.services.extraction_constants import REQUIRED_QUESTIONS


class TestIDEA03TimePeriodContext:
    """IDEA-03: Questions should include time period context."""

    def test_frequency_question_includes_time_period(self) -> None:
        """IDEA-03: Frequency question should include 'per week' or 'weekly' context."""
        freq_q = next((q for q in REQUIRED_QUESTIONS if q["key"] == "frequency"), None)
        assert freq_q is not None, "frequency question should exist"
        question_lower = freq_q["question"].lower()
        assert "per week" in question_lower or "weekly" in question_lower or "week" in question_lower, \
            f"Frequency question should include time period context, got: {freq_q['question']}"

    def test_duration_question_includes_time_unit(self) -> None:
        """IDEA-03: Duration question should include 'in hours' or similar time unit."""
        dur_q = next((q for q in REQUIRED_QUESTIONS if q["key"] == "duration"), None)
        assert dur_q is not None, "duration question should exist"
        question_lower = dur_q["question"].lower()
        assert "hour" in question_lower or "minutes" in question_lower or "time" in question_lower, \
            f"Duration question should include time unit context, got: {dur_q['question']}"
