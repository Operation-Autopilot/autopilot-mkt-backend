"""Service for extracting greenlight actions (team invites, target dates) from conversations."""

import json
import logging
from typing import Any
from uuid import UUID

from openai import OpenAIError

from src.core.config import get_settings
from src.core.openai import get_openai_client
from src.services.conversation_service import ConversationService

logger = logging.getLogger(__name__)

GREENLIGHT_EXTRACTION_SYSTEM_PROMPT = """You extract structured greenlight deployment data from conversation messages.

Extract ONLY information the user has explicitly stated. Do NOT infer or guess.

You extract two types of data:
1. **Team members** the user wants to invite — extract email, name, and role if provided.
2. **Target start date** for deployment — extract as an ISO 8601 date string (YYYY-MM-DD).

Rules:
- Only extract emails that look valid (contain @ and a domain).
- If the user mentions a name without an email, do NOT include that person.
- For dates, resolve relative references (e.g. "next month", "April 1st") relative to the current date context.
- If no team members or dates are mentioned, return empty arrays / null.
- Do NOT extract data the agent said — only extract data from USER messages."""

GREENLIGHT_EXTRACTION_USER_PROMPT = """Extract team members and target start date from this conversation.

Today's date: {today}

Recent conversation:
{conversation_messages}

Extract any team member emails and target deployment date the user mentioned."""

GREENLIGHT_EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "team_members": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email address"},
                    "name": {
                        "type": ["string", "null"],
                        "description": "Full name if provided",
                    },
                    "role": {
                        "type": ["string", "null"],
                        "description": "Role/title if provided",
                    },
                },
                "required": ["email", "name", "role"],
                "additionalProperties": False,
            },
            "description": "Team members the user wants to invite",
        },
        "target_start_date": {
            "type": ["string", "null"],
            "description": "ISO 8601 date (YYYY-MM-DD) for target deployment start, or null",
        },
    },
    "required": ["team_members", "target_start_date"],
    "additionalProperties": False,
}


class GreenlightExtractionService:
    """Extracts greenlight actions from conversation messages using LLM."""

    EXTRACTION_MODEL = "gpt-4o-mini"
    MAX_MESSAGES = 4

    def __init__(
        self,
        conversation_service: ConversationService | None = None,
    ) -> None:
        self.settings = get_settings()
        self.client = get_openai_client()
        self.conversation_service = conversation_service or ConversationService()

    async def extract_greenlight_actions(
        self,
        conversation_id: UUID,
    ) -> dict[str, Any]:
        """Extract team members and target date from recent conversation messages.

        Returns:
            dict with 'team_members' (list) and 'target_start_date' (str|None).
        """
        if self.settings.mock_openai:
            return {"team_members": [], "target_start_date": None}

        try:
            messages = await self.conversation_service.get_recent_messages(
                conversation_id, limit=self.MAX_MESSAGES
            )

            if len(messages) < 2:
                return {"team_members": [], "target_start_date": None}

            conversation_text = "\n".join(
                f"{msg['role'].upper()}: {msg['content']}" for msg in messages
            )

            from datetime import date

            response = await self.client.chat.create(
                model=self.EXTRACTION_MODEL,
                messages=[
                    {"role": "system", "content": GREENLIGHT_EXTRACTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": GREENLIGHT_EXTRACTION_USER_PROMPT.format(
                            today=date.today().isoformat(),
                            conversation_messages=conversation_text,
                        ),
                    },
                ],
                response_format={
                    "type": "json_schema",
                    "json_schema": {
                        "name": "greenlight_extraction",
                        "schema": GREENLIGHT_EXTRACTION_SCHEMA,
                        "strict": True,
                    },
                },
                temperature=0.0,
                max_completion_tokens=500,
            )

            content = response.choices[0].message.content or "{}"
            result = json.loads(content)

            team_members = result.get("team_members", [])
            # Filter out entries without valid-looking emails
            team_members = [
                m for m in team_members if m.get("email") and "@" in m["email"]
            ]

            target_date = result.get("target_start_date")

            if team_members or target_date:
                logger.info(
                    "Greenlight extraction from conversation %s: %d members, date=%s",
                    conversation_id,
                    len(team_members),
                    target_date,
                )

            return {
                "team_members": team_members,
                "target_start_date": target_date,
            }

        except (OpenAIError, json.JSONDecodeError) as e:
            logger.error("Greenlight extraction failed: %s", e)
            return {"team_members": [], "target_start_date": None}
        except Exception as e:
            logger.error("Unexpected greenlight extraction error: %s", e)
            return {"team_members": [], "target_start_date": None}
