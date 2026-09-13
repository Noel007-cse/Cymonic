import os
import json
import re
from groq import Groq
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import Optional, List
from agent.prompts import SYSTEM_PROMPT, EXTRACT_PROMPT

load_dotenv()

_api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=_api_key)
MODEL = "llama-3.3-70b-versatile"

REQUIRED_FIELDS = ["name", "phone", "budget_max", "location", "property_type", "bedrooms", "timeline_days"]


class BuyerProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    timeline_days: Optional[int] = None
    missing_fields: List[str] = Field(default_factory=list)
    is_complete: bool = False


def chat_with_agent(messages: list, buyer_state: dict) -> tuple:
    """
    Send messages to Groq agent and get response + updated buyer state.
    Returns: (ai_message, updated_buyer_state, is_complete)
    """
    system_with_state = SYSTEM_PROMPT + f"\n\nCURRENT KNOWN BUYER STATE:\n{json.dumps(buyer_state, ensure_ascii=False)}"

    groq_messages = [{"role": "system", "content": system_with_state}] + messages

    response = client.chat.completions.create(
        model=MODEL,
        messages=groq_messages,
        temperature=0.3,
        max_tokens=1024,
    )

    ai_content = response.choices[0].message.content
    updated_state = buyer_state.copy()
    is_complete = False

    # Parse [STATE] block
    state_match = re.search(r'\[STATE\]\s*\n?(\{.*?\})', ai_content, re.DOTALL)
    if state_match:
        try:
            state_data = json.loads(state_match.group(1))
            for key, value in state_data.items():
                if value is not None and value != "" and value != 0:
                    updated_state[key] = value
        except (json.JSONDecodeError, ValueError):
            pass

    # Parse [COLLECTED] block
    collected_match = re.search(r'\[COLLECTED\]\s*\n?(\{.*?\})', ai_content, re.DOTALL)
    if collected_match:
        try:
            collected_data = json.loads(collected_match.group(1))
            for key, value in collected_data.items():
                if value is not None and value != "" and value != 0:
                    updated_state[key] = value
            if collected_data.get("missing_fields") == []:
                is_complete = True
        except (json.JSONDecodeError, ValueError):
            pass

    # Clean display message
    clean_message = re.sub(r'\[STATE\]\s*\n?\{.*?\}', '', ai_content, flags=re.DOTALL)
    clean_message = re.sub(r'\[COLLECTED\]\s*\n?\{.*?\}', '', clean_message, flags=re.DOTALL)
    clean_message = clean_message.strip()

    # Check completeness
    missing = check_missing_fields(updated_state)
    if not missing:
        is_complete = True

    return clean_message, updated_state, is_complete


def check_missing_fields(buyer_state: dict) -> list:
    """Return list of required fields not yet collected."""
    missing = []
    for field in REQUIRED_FIELDS:
        val = buyer_state.get(field)
        if val is None or val == "" or val == 0:
            missing.append(field)
    return missing


def get_initial_greeting() -> str:
    """Return the initial greeting from the AI."""
    return "Hi! I'm your Real Estate Assistant. I'm here to help you find your perfect property in Kerala. To get started, could I know your name?"
