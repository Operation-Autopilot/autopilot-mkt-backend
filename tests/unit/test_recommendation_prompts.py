"""Unit tests for recommendation_prompts — BUG-12: Mixed contextual references."""

import pytest

from src.services.recommendation_prompts import format_discovery_context


class TestFormatDiscoveryContextFacilityLabel:
    """BUG-12: 'courts/areas' should not appear for non-court facilities."""

    def _make_answers(self, company_type: str, courts_count: str = "6") -> dict:
        return {
            "company_type": {"value": company_type},
            "courts_count": {"value": courts_count},
        }

    def test_warehouse_uses_loading_bays(self) -> None:
        """Warehouse facility should use 'loading bays/zones', not 'courts'."""
        result = format_discovery_context(self._make_answers("Warehouse"))
        assert "courts" not in result.lower()
        assert "loading bays" in result.lower() or "zones" in result.lower()

    def test_restaurant_uses_dining_areas(self) -> None:
        """Restaurant facility should use 'dining areas/zones', not 'courts'."""
        result = format_discovery_context(self._make_answers("Restaurant"))
        assert "courts" not in result.lower()
        assert "dining" in result.lower() or "zones" in result.lower()

    def test_pickleball_club_keeps_courts(self) -> None:
        """Pickleball Club should keep 'courts'."""
        result = format_discovery_context(self._make_answers("Pickleball Club"))
        assert "courts" in result.lower()

    def test_tennis_club_keeps_courts(self) -> None:
        """Tennis Club should keep 'courts'."""
        result = format_discovery_context(self._make_answers("Tennis Club"))
        assert "courts" in result.lower()

    def test_datacenter_uses_server_rooms(self) -> None:
        """Datacenter facility should use 'server rooms/zones', not 'courts'."""
        result = format_discovery_context(self._make_answers("Datacenter"))
        assert "courts" not in result.lower()
        assert "server" in result.lower() or "zones" in result.lower()

    def test_unknown_type_uses_areas(self) -> None:
        """Unknown facility type should use generic 'areas/zones' fallback."""
        result = format_discovery_context(self._make_answers("Unknown Facility"))
        assert "courts" not in result.lower()
        assert "areas" in result.lower() or "zones" in result.lower()

    def test_no_company_type_uses_areas(self) -> None:
        """No company_type at all should use generic 'areas/zones'."""
        answers = {"courts_count": {"value": "6"}}
        result = format_discovery_context(answers)
        assert "courts" not in result.lower()
        assert "areas" in result.lower() or "zones" in result.lower()
