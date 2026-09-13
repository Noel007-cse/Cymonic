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
MODEL = "openai/gpt-oss-120b"

REQUIRED_FIELDS = [
    "name", "phone", "budget_max", "location", "property_type", "bedrooms",
    "timeline_days", "purpose", "parking", "financing", "amenities",
]
# size_sqft is optional (nice to have but not blocking)
OPTIONAL_FIELDS = ["size_min_sqft", "size_max_sqft"]

ALL_FIELDS = [
    "name", "phone", "budget_max", "location", "property_type", "bedrooms",
    "timeline_days", "purpose", "parking", "size_min_sqft", "financing", "amenities",
]


class BuyerProfile(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    budget_min: Optional[int] = None
    budget_max: Optional[int] = None
    location: Optional[str] = None
    property_type: Optional[str] = None
    bedrooms: Optional[int] = None
    timeline_days: Optional[int] = None
    purpose: Optional[str] = None          # Self-use / Investment
    parking: Optional[str] = None          # Yes / No / Preferable
    size_min_sqft: Optional[int] = None
    size_max_sqft: Optional[int] = None
    financing: Optional[str] = None        # Self-funded / Home loan / Partially financed / Not decided
    amenities: Optional[List[str]] = None  # e.g. ["gym", "pool", "security"]
    missing_fields: List[str] = Field(default_factory=list)
    is_complete: bool = False


def compute_pydynite_score(buyer_state: dict) -> dict:
    """
    PyDynite marking scheme:
    Evaluate each of the 12 questions and return per-field scores + total out of 100.
    """
    scores = {}

    # 1. Name (5 pts)
    scores["name"] = 5 if buyer_state.get("name") else 0

    # 2. Phone (5 pts)
    scores["phone"] = 5 if buyer_state.get("phone") else 0

    # 3. Budget (20 pts)
    bmax = buyer_state.get("budget_max", 0) or 0
    if bmax >= 10_000_000:   # 1 Cr+
        scores["budget"] = 20
    elif bmax >= 5_000_000:  # 50L+
        scores["budget"] = 15
    elif bmax > 0:
        scores["budget"] = 10
    else:
        scores["budget"] = 0

    # 4. Location (10 pts)
    loc = buyer_state.get("location", "") or ""
    scores["location"] = 10 if len(loc.strip()) >= 3 else 0

    # 5. Property type (8 pts)
    scores["property_type"] = 8 if buyer_state.get("property_type") else 0

    # 6. Bedrooms (8 pts)
    scores["bedrooms"] = 8 if buyer_state.get("bedrooms") else 0

    # 7. Timeline (15 pts)
    td = buyer_state.get("timeline_days", 0) or 0
    if td <= 0:
        scores["timeline"] = 0
    elif td <= 30:
        scores["timeline"] = 15
    elif td <= 90:
        scores["timeline"] = 12
    elif td <= 180:
        scores["timeline"] = 8
    elif td <= 365:
        scores["timeline"] = 5
    else:
        scores["timeline"] = 2

    # 8. Purpose (5 pts)
    purpose = buyer_state.get("purpose", "") or ""
    scores["purpose"] = 5 if purpose.strip() else 0

    # 9. Parking (4 pts)
    parking = buyer_state.get("parking", "") or ""
    scores["parking"] = 4 if parking.strip() else 0

    # 10. Size sqft (5 pts)
    smin = buyer_state.get("size_min_sqft", 0) or 0
    smax = buyer_state.get("size_max_sqft", 0) or 0
    scores["size_sqft"] = 5 if (smin > 0 or smax > 0) else 0

    # 11. Financing (5 pts)
    financing = buyer_state.get("financing", "") or ""
    scores["financing"] = 5 if financing.strip() else 0

    # 12. Amenities (10 pts)
    amenities = buyer_state.get("amenities") or []
    if isinstance(amenities, list) and len(amenities) >= 3:
        scores["amenities"] = 10
    elif isinstance(amenities, list) and len(amenities) >= 1:
        scores["amenities"] = 6
    elif isinstance(amenities, str) and len(amenities) > 2:
        scores["amenities"] = 6
    else:
        scores["amenities"] = 0

    total = sum(scores.values())
    answered = sum(1 for v in scores.values() if v > 0)
    return {
        "scores": scores,
        "total": total,
        "max": 100,
        "answered": answered,
        "total_questions": 12,
    }


def chat_with_agent(messages: list, buyer_state: dict) -> tuple:
    """
    Send messages to Groq agent and get response + updated buyer state.
    Returns: (ai_message, updated_buyer_state, is_complete)
    """
    pydynite = compute_pydynite_score(buyer_state)
    system_with_state = (
        SYSTEM_PROMPT
        + f"\n\nCURRENT KNOWN BUYER STATE:\n{json.dumps(buyer_state, ensure_ascii=False)}"
        + f"\n\nCURRENT PYDYNITE SCORE: {pydynite['total']}/100 ({pydynite['answered']}/12 answered)"
    )

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

    # Check completeness against required fields
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
        elif isinstance(val, list) and len(val) == 0:
            missing.append(field)
    return missing


def get_initial_greeting() -> str:
    """Return the initial greeting from the AI."""
    return (
        "Hi! I'm your Real Estate Assistant. I'm here to help you find your perfect property in Kerala. "
        "I'll ask you 12 quick questions to understand your requirements and match you with the best properties. "
        "Let's get started — what's your **full name**?"
    )
