"""Tests for ROI service calculation correctness."""
import pytest
from src.services.roi_service import ROIService
from src.schemas.roi import ROIInputs


class TestROICalculation:
    """Tests for ROI calculation accuracy."""

    def test_expensive_robot_shows_negative_savings(self):
        """Robot costing more than manual spend should show negative monthly savings."""
        service = ROIService()

        # Robot costs $5000/mo but manual spend is only $500/mo
        robot = {
            "monthly_lease": 5000,
            "time_efficiency": 0.8,
            "purchase_price": 180000,
        }
        inputs = ROIInputs(
            labor_rate=15.0,
            utilization=1.0,
            maintenance_factor=0.05,
            manual_monthly_spend=500.0,
            manual_monthly_hours=20.0,
        )

        result = service.calculate_roi(robot, inputs)

        # When robot costs 10x more than manual labor, savings should be negative
        assert result.estimated_monthly_savings < 0, (
            f"Expected negative savings but got {result.estimated_monthly_savings}"
        )

    def test_no_artificial_minimum_floor(self):
        """No artificial minimum floor should be applied to savings."""
        service = ROIService()

        # Set up scenario where raw savings would be slightly negative
        robot = {
            "monthly_lease": 2000,
            "time_efficiency": 0.5,
            "purchase_price": 72000,
        }
        inputs = ROIInputs(
            labor_rate=10.0,
            utilization=1.0,
            maintenance_factor=0.05,
            manual_monthly_spend=800.0,
            manual_monthly_hours=10.0,
        )

        result = service.calculate_roi(robot, inputs)

        # If raw calculation is negative, it should stay negative (no floor)
        # The old code had max(raw_savings, robot_cost * 0.15) as floor
        min_floor_value = 2000 * 0.15  # 300 — old floor
        if result.estimated_monthly_savings > 0:
            # If positive, that's fine — but it shouldn't be exactly the floor value
            assert abs(result.estimated_monthly_savings - min_floor_value) > 0.01, \
                "Savings appears to be using the old artificial floor"

    def test_benefit_multipliers_capped(self):
        """Total benefits should not exceed reasonable bounds."""
        service = ROIService()

        robot = {
            "monthly_lease": 1000,
            "time_efficiency": 0.9,
            "purchase_price": 36000,
        }
        inputs = ROIInputs(
            labor_rate=25.0,
            utilization=1.0,
            maintenance_factor=0.05,
            manual_monthly_spend=3000.0,
            manual_monthly_hours=80.0,
        )

        result = service.calculate_roi(robot, inputs)

        # Gross savings should not be more than 2x the base savings
        # (base = max of cost_eliminated, labor_value))
        base_savings = max(
            3000.0 * 0.9,  # cost_eliminated
            80.0 * 0.9 * 25.0 * 1.35,  # labor_value
        )

        # total savings + robot cost + maintenance = gross
        gross = result.estimated_monthly_savings + 1000 + (1000 * 0.05)
        assert gross < base_savings * 2, (
            f"Gross savings {gross} exceeds 2x base {base_savings * 2}"
        )
