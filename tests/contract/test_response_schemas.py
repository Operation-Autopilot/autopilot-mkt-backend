"""Contract tests for response schema validation.

Validates that Pydantic schemas are self-consistent and that
example/seed data satisfies schema constraints.
"""

import copy
from datetime import datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from tests.flow.conftest import COMPLETE_DISCOVERY_ANSWERS, SEED_ROBOTS


class TestSessionResponseSchema:
    """Validate SessionResponse schema constraints."""

    def test_valid_session_response(self):
        from src.schemas.session import SessionResponse

        data = SessionResponse(
            id=uuid4(),
            session_token="abc123",
            current_question_index=0,
            phase="discovery",
            answers={},
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            ready_for_roi=False,
        )
        assert data.phase == "discovery"

    def test_phase_accepts_any_string(self):
        """SessionResponse.phase is typed as `str`, not Literal — accepts any value."""
        from src.schemas.session import SessionResponse

        data = SessionResponse(
            id=uuid4(),
            current_question_index=0,
            phase="custom_phase",
            answers={},
            expires_at=datetime.utcnow(),
            created_at=datetime.utcnow(),
            ready_for_roi=False,
        )
        assert data.phase == "custom_phase"

    def test_session_update_rejects_invalid_phase(self):
        """SessionUpdate.phase IS a Literal — rejects invalid values."""
        from src.schemas.session import SessionUpdate

        with pytest.raises(ValidationError):
            SessionUpdate(phase="invalid_phase")

    def test_discovery_answer_schema(self):
        from src.schemas.session import DiscoveryAnswerSchema

        answer = DiscoveryAnswerSchema(
            questionId=1,
            key="company_name",
            label="Company Name",
            value="Test Corp",
            group="Company",
        )
        assert answer.key == "company_name"
        assert answer.group == "Company"

    def test_invalid_answer_group_rejected(self):
        from src.schemas.session import DiscoveryAnswerSchema

        with pytest.raises(ValidationError):
            DiscoveryAnswerSchema(
                questionId=1,
                key="company_name",
                label="Company Name",
                value="Test Corp",
                group="InvalidGroup",
            )


class TestRecommendationsResponseSchema:
    """Validate RecommendationsResponse schema constraints."""

    def test_valid_recommendation(self):
        from src.schemas.roi import (
            RecommendationReason,
            RecommendationsResponse,
            RobotRecommendation,
            ROICalculation,
        )

        roi = ROICalculation(
            current_monthly_cost=3000,
            robot_monthly_cost=800,
            estimated_monthly_savings=2200,
            estimated_yearly_savings=26400,
            current_monthly_hours=60,
            hours_saved_monthly=50,
            roi_percent=175,
            payback_months=4.5,
            confidence="high",
            algorithm_version="1.0.0",
        )

        rec = RobotRecommendation(
            robot_id=uuid4(),
            robot_name="TestBot",
            vendor="TestVendor",
            category="Floor Scrubber",
            monthly_lease=800,
            time_efficiency=0.85,
            rank=1,
            label="RECOMMENDED",
            match_score=85.0,
            reasons=[
                RecommendationReason(
                    factor="Cleaning Method",
                    explanation="Matches your vacuum needs",
                    score_impact=25.0,
                )
            ],
            summary="Great fit for your facility",
            projected_roi=roi,
        )

        response = RecommendationsResponse(
            recommendations=[rec],
            total_robots_evaluated=6,
            algorithm_version="3.0.0",
            generated_at=datetime.utcnow(),
        )
        assert len(response.recommendations) == 1
        assert response.recommendations[0].label == "RECOMMENDED"

    def test_match_score_bounded(self):
        """match_score must be between 0 and 100."""
        from src.schemas.roi import RobotRecommendation, ROICalculation

        roi = ROICalculation(
            current_monthly_cost=0,
            robot_monthly_cost=0,
            estimated_monthly_savings=0,
            estimated_yearly_savings=0,
            current_monthly_hours=0,
            hours_saved_monthly=0,
            roi_percent=0,
            confidence="low",
        )

        with pytest.raises(ValidationError):
            RobotRecommendation(
                robot_id=uuid4(),
                robot_name="Test",
                vendor="Test",
                category="Test",
                monthly_lease=0,
                time_efficiency=0,
                rank=1,
                label="RECOMMENDED",
                match_score=150.0,  # Over 100
                summary="test",
                projected_roi=roi,
            )

    def test_invalid_label_rejected(self):
        from src.schemas.roi import RobotRecommendation, ROICalculation

        roi = ROICalculation(
            current_monthly_cost=0,
            robot_monthly_cost=0,
            estimated_monthly_savings=0,
            estimated_yearly_savings=0,
            current_monthly_hours=0,
            hours_saved_monthly=0,
            roi_percent=0,
            confidence="low",
        )

        with pytest.raises(ValidationError):
            RobotRecommendation(
                robot_id=uuid4(),
                robot_name="Test",
                vendor="Test",
                category="Test",
                monthly_lease=0,
                time_efficiency=0,
                rank=1,
                label="INVALID_LABEL",
                match_score=50.0,
                summary="test",
                projected_roi=roi,
            )


class TestMessageResponseSchema:
    """Validate MessageResponse and MessageWithAgentResponse schemas."""

    def test_valid_message_response(self):
        from src.schemas.message import MessageResponse

        msg = MessageResponse(
            id=uuid4(),
            conversation_id=uuid4(),
            role="assistant",
            content="Hello!",
            created_at=datetime.utcnow(),
        )
        assert msg.role == "assistant"

    def test_discovery_state_schema(self):
        from src.schemas.message import DiscoveryState

        state = DiscoveryState(
            ready_for_roi=False,
            answered_keys=["company_name", "company_type"],
            missing_keys=["courts_count", "method", "frequency", "duration", "monthly_spend"],
            progress_percent=28,
        )
        assert len(state.answered_keys) == 2
        assert len(state.missing_keys) == 5


class TestROIInputsSchema:
    """Validate ROI input schemas."""

    def test_valid_roi_inputs(self):
        from src.schemas.session import ROIInputsSchema

        inputs = ROIInputsSchema(
            laborRate=25.0,
            utilization=0.85,
            maintenanceFactor=0.05,
            manualMonthlySpend=3000.0,
            manualMonthlyHours=60.0,
        )
        assert inputs.laborRate == 25.0

    def test_to_roi_inputs_conversion(self):
        from src.schemas.session import ROIInputsSchema

        inputs = ROIInputsSchema(
            laborRate=25.0,
            utilization=0.85,
            maintenanceFactor=0.05,
            manualMonthlySpend=3000.0,
            manualMonthlyHours=60.0,
        )
        converted = inputs.to_roi_inputs()
        assert converted["labor_rate"] == 25.0
        assert converted["manual_monthly_spend"] == 3000.0

    def test_negative_values_rejected(self):
        from src.schemas.session import ROIInputsSchema

        with pytest.raises(ValidationError):
            ROIInputsSchema(
                laborRate=-5.0,
                utilization=0.85,
                maintenanceFactor=0.05,
                manualMonthlySpend=3000.0,
                manualMonthlyHours=60.0,
            )


class TestSeedDataValidation:
    """Ensure test seed data satisfies schema constraints."""

    def test_seed_robots_have_required_fields(self):
        """All seed robots have fields needed by recommendation service."""
        required_fields = [
            "id", "name", "vendor", "category", "monthly_lease",
            "time_efficiency", "active", "modes", "surfaces",
        ]
        for robot in SEED_ROBOTS:
            for field in required_fields:
                assert field in robot, f"Seed robot {robot['name']} missing {field}"

    def test_complete_answers_match_required_keys(self):
        """COMPLETE_DISCOVERY_ANSWERS has all 7 required question keys."""
        from src.services.extraction_constants import REQUIRED_QUESTION_KEYS

        for key in REQUIRED_QUESTION_KEYS:
            assert key in COMPLETE_DISCOVERY_ANSWERS, f"Missing answer for {key}"

    def test_complete_answers_valid_schema(self):
        """Each answer in COMPLETE_DISCOVERY_ANSWERS satisfies DiscoveryAnswerSchema."""
        from src.schemas.session import DiscoveryAnswerSchema

        for key, answer_dict in COMPLETE_DISCOVERY_ANSWERS.items():
            # Should not raise
            schema = DiscoveryAnswerSchema(**answer_dict)
            assert schema.key == key
