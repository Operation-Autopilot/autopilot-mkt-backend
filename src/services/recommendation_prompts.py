"""LLM prompts and schemas for intelligent robot recommendations."""

# System prompt for robot scoring
SCORING_SYSTEM_PROMPT = """You are an expert robotics procurement consultant specializing in commercial cleaning robots.

Your task is to score and rank robots for a customer based on their specific needs.

SCORING CRITERIA (total 100 points):
1. Facility Type Match (0-30): How well the robot's capabilities match the facility type
   - Court-specialized robots for sports facilities
   - For sports clubs, consider courts_count — larger venues (8+ courts) benefit from robots with higher coverage rates and 'large' or 'multi-court' positioning
   - Compact robots for restaurants/retail
   - Industrial robots for warehouses/datacenters

2. Cleaning Method Compatibility (0-25): Match between robot modes and required cleaning methods
   - Vacuum, mop, scrub, sweep capabilities
   - Multi-mode robots score higher for versatile needs

3. Budget Alignment (0-20): How appropriate the robot's price tier is for this customer's spend level
   - monthly_spend represents current cleaning LABOR cost — higher spend = facility justifies higher-tier robot
   - Budget tiers are FACILITY-TYPE-AWARE:
     * Sports clubs (pickleball/tennis) spending $2k–$5k → robots $499–$999/mo are the right tier (courts need quality cleaning); give full points in this range
     * Sports clubs spending <$2k → robots <$500/mo are appropriate
     * Restaurants/retail spending $2k–$5k → robots $400–$800/mo
     * Warehouses/datacenters spending $5k–$10k → robots $1,000–$3,000/mo
     * Spend $10k+/month → robots $900+/month are the right fit; cheap robots under-serve the facility
   - Penalize significant under/over for the tier (e.g., $399 robot for a $10k/month facility = low score)
   - Do NOT simply reward the cheapest option — reward the right tier for the spend level

4. Operational Efficiency (0-15): Time savings and efficiency gains
   - Higher time_efficiency ratings score better
   - Coverage rates and automation level

5. Unique Value Factors (0-10): Special features that address specific pain points
   - Surface compatibility
   - Size/maneuverability for the space
   - Multi-mode robots (4-in-1: scrub+vacuum+sweep+mop) provide more value for sports facilities that need daily varied cleaning than single-mode alternatives
   - Special features relevant to the use case

GUIDELINES:
- Be specific about WHY features matter for THIS customer's situation
- Higher scores = better match, not just more expensive
- Consider the customer's stated priorities
- A perfect match should score 85-95, not always 100
- Differentiate robots clearly - avoid giving everyone similar scores"""

# User prompt template
SCORING_USER_PROMPT_TEMPLATE = """CUSTOMER PROFILE:
{discovery_context}

CANDIDATE ROBOTS TO EVALUATE:
{robots_context}

Score each robot based on how well it matches this customer's specific needs. Provide detailed reasoning.

Return a JSON object with scored_robots array."""

# Structured output schema for LLM scoring
LLM_SCORING_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "robot_scores",
        "schema": {
            "type": "object",
            "properties": {
                "scored_robots": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "robot_index": {
                                "type": "integer",
                                "description": "1-based position index of the robot in the candidate list"
                            },
                            "match_score": {
                                "type": "number",
                                "minimum": 0,
                                "maximum": 100,
                                "description": "Overall match score (0-100)"
                            },
                            "label": {
                                "type": "string",
                                "enum": ["RECOMMENDED", "BEST VALUE", "UPGRADE", "ALTERNATIVE"],
                                "description": "Display label for this recommendation"
                            },
                            "summary": {
                                "type": "string",
                                "description": "One sentence explaining why this robot is recommended for this customer"
                            },
                            "reasons": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "factor": {
                                            "type": "string",
                                            "description": "The scoring factor (e.g., 'Facility Match', 'Budget Fit')"
                                        },
                                        "explanation": {
                                            "type": "string",
                                            "description": "Why this factor matters for this customer"
                                        },
                                        "score_impact": {
                                            "type": "number",
                                            "description": "Points contributed by this factor"
                                        }
                                    },
                                    "required": ["factor", "explanation", "score_impact"],
                                    "additionalProperties": False
                                },
                                "minItems": 2,
                                "maxItems": 4,
                                "description": "Reasons for this score"
                            }
                        },
                        "required": ["robot_index", "match_score", "label", "summary", "reasons"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["scored_robots"],
            "additionalProperties": False
        },
        "strict": True
    }
}


def format_discovery_context(answers: dict) -> str:
    """Format discovery answers into natural language context for LLM.

    Args:
        answers: Dictionary of discovery answers.

    Returns:
        Formatted context string.
    """
    lines = []

    # Company/Facility type
    company_type = _get_answer_value(answers, "company_type")
    if company_type:
        lines.append(f"- Facility Type: {company_type}")

    # Company name
    company_name = _get_answer_value(answers, "company_name")
    if company_name:
        lines.append(f"- Company: {company_name}")

    # Size/Courts - use facility-aware label
    courts_count = _get_answer_value(answers, "courts_count")
    if courts_count:
        company_type_val = _get_answer_value(answers, "company_type") or ""
        size_label = {
            "Pickleball Club": "courts",
            "Tennis Club": "courts",
            "Warehouse": "loading bays/zones",
            "Restaurant": "dining areas/zones",
            "Datacenter": "server rooms/zones",
        }.get(company_type_val, "areas/zones")
        lines.append(f"- Size: {courts_count} {size_label}")

    # Cleaning method
    method = _get_answer_value(answers, "method")
    if method:
        lines.append(f"- Primary Cleaning Method Needed: {method}")

    # Duration/Time
    duration = _get_answer_value(answers, "duration")
    if duration:
        lines.append(f"- Daily Cleaning Duration: {duration}")

    # Budget
    monthly_spend = _get_answer_value(answers, "monthly_spend")
    if monthly_spend:
        lines.append(f"- Current Monthly Cleaning Budget: {monthly_spend}")

    # Add any additional context from other answers
    for key, answer in answers.items():
        if key not in ["company_type", "company_name", "courts_count", "method", "duration", "monthly_spend"]:
            value = _get_answer_value(answers, key)
            if value:
                # Convert key to readable label
                label = key.replace("_", " ").title()
                lines.append(f"- {label}: {value}")

    return "\n".join(lines) if lines else "No specific requirements provided."


def format_robots_context(robots: list[dict]) -> str:
    """Format robot catalog data for LLM scoring context.

    Args:
        robots: List of robot dictionaries from catalog.

    Returns:
        Formatted robots context string.
    """
    lines = []

    for i, robot in enumerate(robots, 1):
        name = robot.get("name", "Unknown Robot")
        category = robot.get("category", "Robot")
        best_for = robot.get("best_for", "general use")
        modes = robot.get("modes", [])
        surfaces = robot.get("surfaces", [])
        monthly_lease = robot.get("monthly_lease", 0)
        time_efficiency = robot.get("time_efficiency", 0.8)
        key_reasons = robot.get("key_reasons", [])

        lines.append(f"\n{i}. {name}")
        lines.append(f"   Category: {category}")
        lines.append(f"   Best For: {best_for}")
        lines.append(f"   Cleaning Modes: {', '.join(modes) if modes else 'N/A'}")
        lines.append(f"   Supported Surfaces: {', '.join(surfaces) if surfaces else 'All surfaces'}")
        lines.append(f"   Monthly Cost: ${float(monthly_lease):,.0f}")
        lines.append(f"   Time Efficiency: {float(time_efficiency) * 100:.0f}%")
        if key_reasons:
            lines.append(f"   Key Features: {'; '.join(key_reasons[:3])}")

    return "\n".join(lines)


def _get_answer_value(answers: dict, key: str) -> str | None:
    """Safely extract and sanitize value from a discovery answer.

    Handles boolean-like strings ("true"/"false") by converting to "Yes"/"No".

    Args:
        answers: Dictionary of answers.
        key: Answer key to extract.

    Returns:
        The sanitized value string or None.
    """
    answer = answers.get(key)
    if answer is None:
        return None
    if isinstance(answer, dict):
        value = str(answer.get("value", ""))
    else:
        value = str(answer) if answer else ""

    if not value:
        return None

    # Convert boolean-like strings to readable format
    value_lower = value.lower().strip()
    if value_lower == "true":
        return "Yes"
    elif value_lower == "false":
        return "No"

    return value
