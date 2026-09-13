def format_inr(amount) -> str:
    """Format amount in Indian Rupee shorthand notation."""
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return "Not specified"
    if not amount or amount == 0:
        return "Not specified"
    if amount >= 10000000:
        return f"Rs{amount/10000000:.1f} Cr"
    elif amount >= 100000:
        return f"Rs{amount/100000:.0f}L"
    return f"Rs{amount:,.0f}"


def format_inr_full(amount) -> str:
    """Format amount as full INR number."""
    try:
        return f"Rs{int(float(amount)):,}"
    except (TypeError, ValueError):
        return "Not specified"


def get_status_emoji(status: str) -> str:
    return {
        "HIGHLY_QUALIFIED": "🟢",
        "QUALIFIED": "🟡",
        "NEEDS_INFORMATION": "🔵",
        "LOW_PRIORITY": "🟠",
        "UNQUALIFIED": "🔴",
        "NO_MATCH": "⚫",
        "NEW": "⚪",
    }.get(status, "⚪")


def get_priority_badge(priority: str) -> str:
    return {"HIGH": "🔴 HIGH", "MEDIUM": "🟡 MEDIUM", "LOW": "⚪ LOW"}.get(priority, priority)


def timeline_days_to_text(days) -> str:
    try:
        days = int(days)
    except (TypeError, ValueError):
        return "Not specified"
    if not days:
        return "Not specified"
    if days <= 30:
        return f"Within {days} days"
    elif days <= 90:
        months = round(days / 30)
        return f"Within {months} month{'s' if months > 1 else ''}"
    elif days <= 365:
        months = round(days / 30)
        return f"Within {months} months"
    years = round(days / 365)
    return f"Within {years} year{'s' if years > 1 else ''}"
