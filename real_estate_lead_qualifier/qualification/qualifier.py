from typing import List


def score_budget_clarity(buyer_state: dict) -> int:
    """0-20: How clearly budget is specified."""
    budget_max = buyer_state.get("budget_max")
    if not budget_max or budget_max <= 0:
        return 0
    return 20 if buyer_state.get("budget_min") else 15


def score_location_clarity(buyer_state: dict) -> int:
    """0-15: How clearly location is specified."""
    location = buyer_state.get("location", "")
    if not location:
        return 0
    return 15 if len(location.strip()) >= 3 else 5


def score_property_requirement(buyer_state: dict) -> int:
    """0-15: How clearly property requirements are specified."""
    score = 0
    if buyer_state.get("property_type"):
        score += 7
    if buyer_state.get("bedrooms"):
        score += 8
    return score


def score_timeline_quality(buyer_state: dict) -> int:
    """0-20: Timeline clarity and urgency."""
    td = buyer_state.get("timeline_days")
    if not td or td <= 0:
        return 0
    if td <= 30:
        return 20
    elif td <= 60:
        return 18
    elif td <= 90:
        return 15
    elif td <= 180:
        return 10
    elif td <= 365:
        return 7
    return 3


def score_match_quality(matched_properties: list) -> int:
    """0-20: Quality of property matches found."""
    if not matched_properties:
        return 0
    best_score = matched_properties[0]["match_score"]
    count_good = sum(1 for p in matched_properties if p["match_score"] >= 70)
    if best_score >= 90 and count_good >= 3:
        return 20
    elif best_score >= 80:
        return 15
    elif best_score >= 70:
        return 12
    elif best_score >= 60:
        return 8
    elif best_score >= 50:
        return 5
    return 0


def score_engagement(buyer_state: dict, message_count: int = 5) -> int:
    """0-10: Buyer engagement level."""
    fields_provided = sum(
        1 for k in ["name", "phone", "budget_max", "location", "property_type", "bedrooms", "timeline_days"]
        if buyer_state.get(k)
    )
    if fields_provided >= 7:
        return 10
    elif fields_provided >= 5:
        return 7
    elif fields_provided >= 3:
        return 4
    return 1


def get_qualification_status(score: int, best_match_score: float, matched_properties: list) -> str:
    if not matched_properties or best_match_score < 40:
        return "NO_MATCH"
    if score >= 80 and best_match_score >= 85 and len(matched_properties) >= 1:
        return "HIGHLY_QUALIFIED"
    elif score >= 60:
        return "QUALIFIED"
    elif score >= 40:
        return "NEEDS_INFORMATION"
    elif score >= 20:
        return "LOW_PRIORITY"
    return "UNQUALIFIED"


def get_priority(status: str) -> str:
    return {
        "HIGHLY_QUALIFIED": "HIGH",
        "QUALIFIED": "MEDIUM",
        "NEEDS_INFORMATION": "MEDIUM",
        "LOW_PRIORITY": "LOW",
        "UNQUALIFIED": "LOW",
        "NO_MATCH": "LOW",
    }.get(status, "LOW")


def get_next_action(status: str) -> str:
    return {
        "HIGHLY_QUALIFIED": "ESCALATE_TO_BROKER",
        "QUALIFIED": "SCHEDULE_SITE_VISIT",
        "NEEDS_INFORMATION": "COLLECT_MORE_INFO",
        "LOW_PRIORITY": "NURTURE",
        "UNQUALIFIED": "CLOSE",
        "NO_MATCH": "NO_MATCH_RECOMMEND_ALTERNATIVES",
    }.get(status, "FOLLOW_UP")


def generate_tags(buyer_state: dict, status: str, matched_properties: list) -> List[str]:
    tags = []
    if buyer_state.get("location"):
        tags.append(buyer_state["location"])
    if buyer_state.get("bedrooms"):
        tags.append(f"{buyer_state['bedrooms']}BHK")
    if buyer_state.get("property_type"):
        tags.append(buyer_state["property_type"])
    td = buyer_state.get("timeline_days", 0) or 0
    if 0 < td <= 60:
        tags += ["Urgent", "HighIntent"]
    elif td <= 180:
        tags.append("MediumIntent")
    if status == "HIGHLY_QUALIFIED":
        tags.append("BrokerAttention")
    if matched_properties and matched_properties[0]["match_score"] >= 85:
        tags.append("StrongMatch")
    return tags


def generate_reasoning(buyer_state: dict, matched_properties: list) -> List[str]:
    reasons = []
    reasons.append(
        "- Budget is clearly specified." if buyer_state.get("budget_max") else "- Budget is not specified."
    )
    loc = buyer_state.get("location")
    reasons.append(
        f"- Location is clearly specified ({loc})." if loc else "- Location is not specified."
    )
    pt = buyer_state.get("property_type")
    beds = buyer_state.get("bedrooms")
    if pt and beds:
        reasons.append(f"- Property requirement is specific ({beds}BHK {pt}).")
    else:
        reasons.append("- Property requirements are incomplete.")
    td = buyer_state.get("timeline_days", 0) or 0
    if td > 0:
        reasons.append(
            f"- Buyer plans to purchase within {td} days (urgent)." if td <= 60
            else f"- Buyer has a defined purchase timeline ({td} days)."
        )
    else:
        reasons.append("- Purchase timeline is not specified.")
    if matched_properties:
        count_good = sum(1 for p in matched_properties if p["match_score"] >= 70)
        best = matched_properties[0]["match_score"]
        reasons.append(f"- {len(matched_properties)} suitable properties found; best match {best:.0f}%.")
    else:
        reasons.append("- No suitable properties found in database.")
    return reasons


def qualify_buyer(buyer_state: dict, matched_properties: list, message_count: int = 5) -> dict:
    """Main qualification function. Returns complete qualification result."""
    score_breakdown = {
        "Budget Clarity": score_budget_clarity(buyer_state),
        "Location Clarity": score_location_clarity(buyer_state),
        "Property Requirement": score_property_requirement(buyer_state),
        "Purchase Timeline": score_timeline_quality(buyer_state),
        "Property Match Quality": score_match_quality(matched_properties),
        "Engagement": score_engagement(buyer_state, message_count),
    }
    total_score = sum(score_breakdown.values())
    best_match_score = matched_properties[0]["match_score"] if matched_properties else 0
    status = get_qualification_status(total_score, best_match_score, matched_properties)
    priority = get_priority(status)
    next_action = get_next_action(status)
    tags = generate_tags(buyer_state, status, matched_properties)
    reasoning = generate_reasoning(buyer_state, matched_properties)
    best_match_property = matched_properties[0]["property_id"] if matched_properties else None
    return {
        "qualification_score": total_score,
        "score_breakdown": score_breakdown,
        "status": status,
        "priority": priority,
        "next_action": next_action,
        "tags": tags,
        "reasoning": reasoning,
        "best_match_property": best_match_property,
        "best_match_score": best_match_score,
        "matched_properties": matched_properties,
    }
