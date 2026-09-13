import pandas as pd
import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
BUYERS_CSV = os.path.join(DATA_DIR, "buyers.csv")
PROPERTIES_CSV = os.path.join(DATA_DIR, "properties.csv")

BUYERS_COLUMNS = [
    "buyer_id", "name", "phone", "email", "budget", "budget_min", "budget_max",
    "location", "property_type", "bedrooms", "timeline", "timeline_days",
    "purpose", "parking", "size_min_sqft", "size_max_sqft", "financing", "amenities",
    "qualification_score", "status", "priority", "best_match_property",
    "best_match_score", "next_action", "created_at", "updated_at",
]


def load_properties() -> pd.DataFrame:
    try:
        df = pd.read_csv(PROPERTIES_CSV)
        df.columns = df.columns.str.strip()
        df["price"] = pd.to_numeric(df["price"], errors="coerce").fillna(0)
        df["bedrooms"] = pd.to_numeric(df["bedrooms"], errors="coerce").fillna(0).astype(int)
        df["bathrooms"] = pd.to_numeric(df["bathrooms"], errors="coerce").fillna(0).astype(int)
        df["area_sqft"] = pd.to_numeric(df["area_sqft"], errors="coerce").fillna(0).astype(int)
        # Add broker columns if not present
        if "broker_phone" not in df.columns:
            df["broker_phone"] = ""
        if "broker_name" not in df.columns:
            df["broker_name"] = ""
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=[
            "property_id", "property_name", "property_type", "location",
            "price", "bedrooms", "bathrooms", "area_sqft", "parking",
            "furnishing", "floor", "total_floors", "property_age",
            "possession", "amenities", "description", "availability",
            "broker_name", "broker_phone",
        ])


def load_buyers() -> pd.DataFrame:
    try:
        df = pd.read_csv(BUYERS_CSV)
        df.columns = df.columns.str.strip()
        return df
    except FileNotFoundError:
        return pd.DataFrame(columns=BUYERS_COLUMNS)


def generate_buyer_id(buyers_df: pd.DataFrame) -> str:
    if buyers_df.empty:
        return "B001"
    nums = []
    for b in buyers_df["buyer_id"].dropna().tolist():
        try:
            nums.append(int(str(b).replace("B", "")))
        except ValueError:
            pass
    return f"B{(max(nums) + 1 if nums else 1):03d}"


def save_buyer(buyer_state: dict, qualification_result: dict) -> str:
    buyers_df = load_buyers()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = buyer_state.get("name", "")
    phone = buyer_state.get("phone", "")
    budget_max = buyer_state.get("budget_max", 0) or 0
    budget_min = buyer_state.get("budget_min", 0) or 0
    timeline_days = buyer_state.get("timeline_days", 0) or 0

    if timeline_days:
        if timeline_days <= 30:
            timeline_str = f"Within {timeline_days} days"
        else:
            months = round(timeline_days / 30)
            timeline_str = f"Within {months} month{'s' if months > 1 else ''}"
    else:
        timeline_str = ""

    # Serialize amenities list to string for CSV
    amenities = buyer_state.get("amenities") or []
    if isinstance(amenities, list):
        amenities_str = ", ".join(amenities)
    else:
        amenities_str = str(amenities)

    buyer_row = {
        "name": name,
        "phone": phone,
        "email": buyer_state.get("email", ""),
        "budget": budget_max,
        "budget_min": budget_min,
        "budget_max": budget_max,
        "location": buyer_state.get("location", ""),
        "property_type": buyer_state.get("property_type", ""),
        "bedrooms": buyer_state.get("bedrooms", 0),
        "timeline": timeline_str,
        "timeline_days": timeline_days,
        "purpose": buyer_state.get("purpose", ""),
        "parking": buyer_state.get("parking", ""),
        "size_min_sqft": buyer_state.get("size_min_sqft", 0) or 0,
        "size_max_sqft": buyer_state.get("size_max_sqft", 0) or 0,
        "financing": buyer_state.get("financing", ""),
        "amenities": amenities_str,
        "qualification_score": qualification_result.get("qualification_score", 0),
        "status": qualification_result.get("status", "NEW"),
        "priority": qualification_result.get("priority", "LOW"),
        "best_match_property": qualification_result.get("best_match_property", ""),
        "best_match_score": qualification_result.get("best_match_score", 0),
        "next_action": qualification_result.get("next_action", ""),
        "updated_at": now,
    }

    # Check if buyer already exists
    mask = None
    if name and not buyers_df.empty and "name" in buyers_df.columns:
        mask = buyers_df["name"].str.lower() == name.lower()

    if mask is not None and mask.any():
        idx = buyers_df[mask].index[0]
        buyer_id = buyers_df.loc[idx, "buyer_id"]
        for col, val in buyer_row.items():
            buyers_df.loc[idx, col] = val
    else:
        buyer_id = generate_buyer_id(buyers_df)
        buyer_row["buyer_id"] = buyer_id
        buyer_row["created_at"] = now
        buyers_df = pd.concat([buyers_df, pd.DataFrame([buyer_row])], ignore_index=True)

    os.makedirs(DATA_DIR, exist_ok=True)
    buyers_df.to_csv(BUYERS_CSV, index=False)
    return buyer_id


def get_dashboard_stats(buyers_df: pd.DataFrame) -> dict:
    stats = {
        "total": len(buyers_df), "highly_qualified": 0, "qualified": 0,
        "needs_information": 0, "low_priority": 0, "no_match": 0, "unqualified": 0,
    }
    if buyers_df.empty or "status" not in buyers_df.columns:
        return stats
    counts = buyers_df["status"].value_counts().to_dict()
    stats["highly_qualified"] = counts.get("HIGHLY_QUALIFIED", 0)
    stats["qualified"] = counts.get("QUALIFIED", 0)
    stats["needs_information"] = counts.get("NEEDS_INFORMATION", 0)
    stats["low_priority"] = counts.get("LOW_PRIORITY", 0)
    stats["no_match"] = counts.get("NO_MATCH", 0)
    stats["unqualified"] = counts.get("UNQUALIFIED", 0)
    return stats
