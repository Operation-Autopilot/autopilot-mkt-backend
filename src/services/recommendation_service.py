"""Intelligent robot recommendation service using deterministic scoring + semantic search.

Scoring is fully deterministic (rule-based + semantic similarity boost).
LLM is only used optionally to generate natural language summaries for
the top recommendations — never for scoring or ranking.
"""

import json
import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from openai import OpenAIError

from src.core.config import get_settings
from src.core.openai import get_openai_client
from src.core.token_budget import TokenBudgetError, get_token_budget
from src.models.session import DiscoveryAnswer
from src.schemas.roi import (
    OtherRobotOption,
    RecommendationReason,
    RecommendationsRequest,
    RecommendationsResponse,
    RobotRecommendation,
    ROIInputs,
)
from src.services.rag_service import RAGService, get_rag_service
from src.services.recommendation_cache import get_recommendation_cache
from src.services.recommendation_prompts import (
    format_discovery_context,
)
from src.services.robot_catalog_service import RobotCatalogService

logger = logging.getLogger(__name__)

# Algorithm version — 3.0 = deterministic scoring + semantic boost + optional LLM summaries
ALGORITHM_VERSION = "3.0.0"

# LLM prompt for generating summaries only (no scoring, no IDs)
SUMMARY_SYSTEM_PROMPT = """You are an expert robotics procurement consultant. Given a customer profile and a ranked list of cleaning robots, write a short personalized summary for each robot explaining why it's a good fit for THIS customer.

GUIDELINES:
- Each summary should be 1-2 sentences
- Be specific about WHY features matter for this customer's situation
- Reference the customer's facility type, cleaning needs, or budget when relevant
- Do NOT include scores, rankings, or robot IDs"""

SUMMARY_USER_PROMPT_TEMPLATE = """CUSTOMER PROFILE:
{discovery_context}

ROBOTS (ranked by match score, best first):
{robots_summary_context}

Write a personalized summary for each robot. Return a JSON object."""

SUMMARY_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "robot_summaries",
        "schema": {
            "type": "object",
            "properties": {
                "summaries": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "robot_name": {
                                "type": "string",
                                "description": "Name of the robot",
                            },
                            "summary": {
                                "type": "string",
                                "description": "1-2 sentence personalized summary",
                            },
                        },
                        "required": ["robot_name", "summary"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["summaries"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


class RecommendationService:
    """Service for robot recommendations using deterministic scoring + semantic search."""

    def __init__(
        self,
        rag_service: RAGService | None = None,
        robot_catalog_service: RobotCatalogService | None = None,
    ) -> None:
        self._rag_service = rag_service
        self._robot_catalog_service = robot_catalog_service
        self.settings = get_settings()
        self.client = get_openai_client()

    @property
    def rag_service(self) -> RAGService:
        if self._rag_service is None:
            self._rag_service = get_rag_service()
        return self._rag_service

    @property
    def robot_catalog(self) -> RobotCatalogService:
        if self._robot_catalog_service is None:
            self._robot_catalog_service = RobotCatalogService()
        return self._robot_catalog_service

    async def get_intelligent_recommendations(
        self,
        request: RecommendationsRequest,
        session_id: UUID | None = None,
        profile_id: UUID | None = None,
        use_cache: bool = True,
    ) -> RecommendationsResponse:
        """Get robot recommendations using deterministic scoring + semantic boost.

        Pipeline:
        1. Build discovery context from answers
        2. Get semantic candidates via RAG (embedding search)
        3. Score candidates deterministically (rule-based + semantic boost)
        4. Optionally generate LLM summaries for top-K (non-blocking)
        5. Build response with ROI calculations

        Args:
            request: Recommendations request with answers.
            session_id: Optional session ID for token budget tracking.
            profile_id: Optional profile ID for token budget tracking.
            use_cache: Whether to use cached recommendations.

        Returns:
            RecommendationsResponse with ranked recommendations.
        """
        # Check cache first
        if use_cache:
            cache = get_recommendation_cache()
            cached = await cache.get(request.answers)
            if cached:
                logger.info("Returning cached recommendations")
                return cached

        try:
            # Step 1: Build natural language context from discovery answers
            discovery_context = format_discovery_context(request.answers)

            # Step 2: Get semantic candidates using RAG
            candidates = await self._get_semantic_candidates(
                discovery_context,
                max_candidates=self.settings.llm_scoring_max_candidates,
            )

            if not candidates:
                logger.warning("No semantic candidates found, falling back to manual")
                return await self._fallback_to_manual(request)

            # Step 3: Score candidates deterministically
            scored = self._score_candidates_deterministic(candidates, request.answers)

            if not scored:
                logger.warning("No scored candidates, falling back to manual")
                return await self._fallback_to_manual(request)

            # Step 4: Optionally enrich top-K with LLM summaries
            scored = await self._enrich_with_llm_summaries(
                scored_candidates=scored,
                discovery_context=discovery_context,
                top_k=request.top_k,
                session_id=session_id,
                profile_id=profile_id,
            )

            # Step 5: Build response with ROI
            response = self._build_response(scored, candidates, request)

            # Cache the response
            if use_cache:
                await cache.set(request.answers, response)

            return response

        except Exception as e:
            logger.error("Error in recommendations: %s", str(e))
            return await self._fallback_to_manual(request)

    async def _get_semantic_candidates(
        self,
        discovery_context: str,
        max_candidates: int = 8,
    ) -> list[dict[str, Any]]:
        """Get robot candidates using semantic search.

        Args:
            discovery_context: Natural language context from discovery.
            max_candidates: Maximum candidates to return.

        Returns:
            List of robot dictionaries with semantic scores attached.
        """
        try:
            search_results = await self.rag_service.search_robots_for_discovery(
                discovery_context=discovery_context,
                top_k=max_candidates,
            )

            if not search_results:
                logger.warning("RAG search returned no results, using all robots")
                robots = await self.robot_catalog.list_robots(active_only=True)
                return robots[:max_candidates]

            # Get full robot data for the candidates
            robot_ids = []
            for r in search_results:
                rid = r.get("robot_id")
                if rid:
                    try:
                        robot_ids.append(UUID(rid))
                    except (ValueError, AttributeError):
                        logger.warning("Skipping invalid robot_id: %s", rid)
            robots = await self.robot_catalog.get_robots_by_ids(robot_ids)

            # Attach semantic scores
            score_map = {r["robot_id"]: r["semantic_score"] for r in search_results}
            for robot in robots:
                robot["_semantic_score"] = score_map.get(str(robot.get("id")), 0.5)

            return robots

        except Exception as e:
            logger.error("Error getting semantic candidates: %s", str(e))
            robots = await self.robot_catalog.list_robots(active_only=True)
            return robots[:max_candidates]

    def _score_candidates_deterministic(
        self,
        candidates: list[dict[str, Any]],
        answers: dict[str, DiscoveryAnswer],
    ) -> list[dict[str, Any]]:
        """Score and rank candidates using rule-based matching + semantic boost.

        No LLM involved. UUIDs never leave Python.

        Args:
            candidates: Robot candidates with _semantic_score attached.
            answers: Discovery answers.

        Returns:
            List of dicts with robot_id, match_score, label, reasons, summary,
            sorted by match_score descending.
        """
        from src.services.roi_service import ROIService

        roi_service = ROIService(robot_catalog_service=self.robot_catalog)

        scored: list[dict[str, Any]] = []
        for robot in candidates:
            # Get base rule-based score and reasons
            base_score, reasons = roi_service._score_robot_manual(robot, answers)

            # Apply semantic similarity boost (up to 15 points)
            semantic_score = float(robot.get("_semantic_score", 0.5))
            semantic_boost = semantic_score * 15.0  # 0-15 points
            reasons.append(
                RecommendationReason(
                    factor="Semantic Relevance",
                    explanation="AI-matched based on your specific requirements",
                    score_impact=round(semantic_boost, 1),
                )
            )

            total_score = min(100.0, base_score + semantic_boost)

            # Generate template summary (will be overwritten by LLM if available)
            robot_name = robot.get("name", "This robot")
            company_type_answer = answers.get("company_type")
            if company_type_answer and isinstance(company_type_answer, dict):
                company_type = str(company_type_answer.get("value", "your facility"))
            else:
                company_type = "your facility"

            if reasons:
                top_reason = max(reasons, key=lambda r: r.score_impact)
                summary = f"{robot_name} excels at {top_reason.factor.lower()} for {company_type}."
            else:
                summary = f"{robot_name} is a solid choice for {company_type}."

            scored.append({
                "robot_id": str(robot.get("id")),
                "_robot_name": robot.get("name", "Unknown"),
                "match_score": round(total_score, 1),
                "reasons": reasons,
                "summary": summary,
            })

        # Sort by score descending
        scored.sort(key=lambda x: x["match_score"], reverse=True)

        # Assign labels based on rank and attributes
        candidate_map = {str(r.get("id")): r for r in candidates}
        for i, s in enumerate(scored):
            robot = candidate_map.get(s["robot_id"])
            if robot:
                s["label"] = self._assign_label(i + 1, s["match_score"], robot)
            else:
                s["label"] = "ALTERNATIVE"

        return scored

    @staticmethod
    def _assign_label(
        rank: int, score: float, robot: dict[str, Any]
    ) -> str:
        """Assign a display label based on rank and robot attributes."""
        if rank == 1:
            return "RECOMMENDED"
        monthly_lease = float(robot.get("monthly_lease", 0))
        if rank == 2 and monthly_lease < 1000 and score >= 60:
            return "BEST VALUE"
        if monthly_lease >= 1200 and score >= 70:
            return "UPGRADE"
        return "ALTERNATIVE"

    async def _enrich_with_llm_summaries(
        self,
        scored_candidates: list[dict[str, Any]],
        discovery_context: str,
        top_k: int = 3,
        session_id: UUID | None = None,
        profile_id: UUID | None = None,
    ) -> list[dict[str, Any]]:
        """Optionally enrich top-K recommendations with LLM-generated summaries.

        If LLM fails, the template summaries from deterministic scoring are kept.
        No UUIDs or IDs are sent to the LLM — only robot names.

        Args:
            scored_candidates: Deterministically scored candidates.
            discovery_context: Customer profile context.
            top_k: Number of top robots to generate summaries for.
            session_id: For token budget tracking.
            profile_id: For token budget tracking.

        Returns:
            Same list with potentially updated summaries for top-K.
        """
        if not self.settings.use_llm_recommendations:
            return scored_candidates

        top_robots = scored_candidates[:top_k]
        if not top_robots:
            return scored_candidates

        # Build summary context using names only (no IDs)
        robots_lines = []
        for i, s in enumerate(top_robots, 1):
            name = s.get("_robot_name", "Robot")
            reasons = s.get("reasons", [])
            reasons_text = ", ".join(
                r.factor if isinstance(r, RecommendationReason) else r.get("factor", "")
                for r in reasons
            )
            robots_lines.append(f"{i}. {name} — Strengths: {reasons_text}")

        robots_summary = "\n".join(robots_lines)

        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            discovery_context=discovery_context,
            robots_summary_context=robots_summary,
        )

        # Check token budget
        budget_key: str | None = None
        is_authenticated = False
        if profile_id:
            budget_key = f"user:{profile_id}"
            is_authenticated = True
        elif session_id:
            budget_key = f"session:{session_id}"

        if budget_key:
            try:
                token_budget = get_token_budget()
                estimated_tokens = len(user_prompt) // 4 + 400
                allowed, remaining, limit = await token_budget.check_budget(
                    budget_key, estimated_tokens, is_authenticated
                )
                if not allowed:
                    logger.info("Token budget exceeded for summaries, using templates")
                    return scored_candidates
            except Exception:
                pass  # Budget check failure shouldn't block recommendations

        try:
            response = await self.client.chat.create(
                model=self.settings.openai_model_scoring,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=SUMMARY_SCHEMA,
                max_completion_tokens=600,
                temperature=0.5,
            )

            # Track token usage
            if budget_key and response.usage:
                token_budget = get_token_budget()
                await token_budget.record_usage(budget_key, response.usage.total_tokens)

            result = json.loads(response.choices[0].message.content or "{}")
            summaries = result.get("summaries", [])

            # Match summaries to scored candidates by name (fuzzy)
            summary_map = {s["robot_name"].lower(): s["summary"] for s in summaries}
            for s in top_robots:
                name = s.get("_robot_name", "").lower()
                if name in summary_map:
                    s["summary"] = summary_map[name]
                else:
                    # Try partial match
                    for sname, summary in summary_map.items():
                        if sname in name or name in sname:
                            s["summary"] = summary
                            break

            logger.info("LLM generated summaries for %d robots", len(summaries))

        except (OpenAIError, json.JSONDecodeError, TokenBudgetError) as e:
            logger.warning("LLM summary generation failed, using templates: %s", str(e))
        except Exception as e:
            logger.warning("Unexpected error in LLM summaries: %s", str(e))

        return scored_candidates

    def _build_response(
        self,
        scored: list[dict[str, Any]],
        candidates: list[dict[str, Any]],
        request: RecommendationsRequest,
    ) -> RecommendationsResponse:
        """Build the final recommendations response.

        All data is deterministic — no LLM output affects ranking or structure.
        """
        from src.services.roi_service import ROIService

        roi_service = ROIService(robot_catalog_service=self.robot_catalog)
        candidate_map = {str(r.get("id")): r for r in candidates}
        inputs = request.roi_inputs or roi_service.derive_roi_inputs(request.answers)

        recommendations: list[RobotRecommendation] = []
        other_options: list[OtherRobotOption] = []
        rank = 1

        for s in scored:
            robot_id_str = s["robot_id"]
            robot = candidate_map.get(robot_id_str)
            if not robot:
                logger.warning("Robot %s not found in candidates", robot_id_str)
                continue

            try:
                robot_id = UUID(robot_id_str)
            except (ValueError, TypeError):
                logger.error("Invalid robot ID: %s", robot_id_str)
                continue

            # Calculate ROI
            roi = roi_service.calculate_roi(robot, inputs, answers=request.answers)

            raw_image_url = robot.get("image_url", "")
            image_urls = (
                [url.strip() for url in raw_image_url.split(",") if url.strip()]
                if raw_image_url
                else []
            )

            # Convert RecommendationReason objects if needed
            reasons = s.get("reasons", [])
            if reasons and not isinstance(reasons[0], RecommendationReason):
                reasons = [
                    RecommendationReason(
                        factor=r.get("factor", "Match"),
                        explanation=r.get("explanation", ""),
                        score_impact=r.get("score_impact", 0),
                    )
                    for r in reasons
                ]

            if rank <= request.top_k:
                recommendations.append(
                    RobotRecommendation(
                        robot_id=robot_id,
                        robot_name=robot.get("name", "Unknown"),
                        vendor=robot.get("vendor", robot.get("manufacturer", "Unknown")),
                        category=robot.get("category", "Cleaning Robot"),
                        monthly_lease=float(robot.get("monthly_lease", 0)),
                        time_efficiency=float(robot.get("time_efficiency", 0.8)),
                        image_urls=image_urls,
                        rank=rank,
                        label=s.get("label", "ALTERNATIVE"),
                        match_score=s["match_score"],
                        reasons=reasons,
                        summary=s.get("summary", "A suitable option for your needs."),
                        projected_roi=roi,
                        modes=robot.get("modes", []),
                        surfaces=robot.get("surfaces", []),
                        key_reasons=robot.get("key_reasons", []),
                        specs=robot.get("specs", []),
                    )
                )
                rank += 1
            else:
                other_options.append(
                    OtherRobotOption(
                        robot_id=robot_id,
                        robot_name=robot.get("name", "Unknown"),
                        vendor=robot.get("vendor", robot.get("manufacturer", "Unknown")),
                        category=robot.get("category", "Cleaning Robot"),
                        monthly_lease=float(robot.get("monthly_lease", 0)),
                        time_efficiency=float(robot.get("time_efficiency", 0.8)),
                        image_urls=image_urls,
                        match_score=s["match_score"],
                        modes=robot.get("modes", []),
                        surfaces=robot.get("surfaces", []),
                        key_reasons=robot.get("key_reasons", []),
                        specs=robot.get("specs", []),
                    )
                )

        # Include any candidates that the LLM didn't score as other_options
        scored_ids = {s.get("robot_id") for s in scored_robots}
        for cand_id_str, robot in candidate_map.items():
            if cand_id_str in scored_ids:
                continue
            try:
                robot_id = UUID(cand_id_str)
            except (ValueError, TypeError):
                continue

            raw_image_url = robot.get("image_url", "")
            image_urls = [url.strip() for url in raw_image_url.split(",") if url.strip()] if raw_image_url else []

            other_options.append(OtherRobotOption(
                robot_id=robot_id,
                robot_name=robot.get("name", "Unknown"),
                vendor=robot.get("vendor", robot.get("manufacturer", "Unknown")),
                category=robot.get("category", "Cleaning Robot"),
                monthly_lease=float(robot.get("monthly_lease", 0)),
                time_efficiency=float(robot.get("time_efficiency", 0.8)),
                image_urls=image_urls,
                match_score=0.0,
                modes=robot.get("modes", []),
                surfaces=robot.get("surfaces", []),
                key_reasons=robot.get("key_reasons", []),
                specs=robot.get("specs", []),
            ))

        return RecommendationsResponse(
            recommendations=recommendations,
            other_options=other_options,
            total_robots_evaluated=len(candidates),
            algorithm_version=ALGORITHM_VERSION,
            generated_at=datetime.utcnow(),
        )

    async def _fallback_to_manual(
        self,
        request: RecommendationsRequest,
    ) -> RecommendationsResponse:
        """Fallback to pure manual scoring (no semantic search)."""
        from src.services.roi_service import ROIService

        logger.info("Using manual scoring fallback")
        roi_service = ROIService(robot_catalog_service=self.robot_catalog)
        return await roi_service.get_recommendations_manual(request)


# Singleton instance
_recommendation_service: RecommendationService | None = None


def get_recommendation_service() -> RecommendationService:
    """Get or create the recommendation service singleton."""
    global _recommendation_service
    if _recommendation_service is None:
        _recommendation_service = RecommendationService()
    return _recommendation_service
