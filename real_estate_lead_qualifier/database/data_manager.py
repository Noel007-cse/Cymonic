import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# ── Supabase client ───────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")

_supabase_client = None


def get_supabase():
    """Lazy-initialise and return the Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_KEY must be set in your .env file."
            )
        from supabase import create_client
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    return _supabase_client


# ── Column definitions (kept for reference / fallback) ───────────────────────
BUYERS_COLUMNS = [
    "buyer_id", "name", "phone", "email", "budget", "budget_min", "budget_max",
    "location", "property_type", "bedrooms", "timeline", "timeline_days",
    "purpose", "parking", "size_min_sqft", "size_max_sqft", "financing", "amenities",
    "qualification_score", "status", "priority", "best_match_property",
    "best_match_score", "next_action", "created_at", "updated_at",
]


# ── Properties ────────────────────────────────────────────────────────────────

def load_properties() -> pd.DataFrame:
    """Load all properties from Supabase."""
    try:
        sb = get_supabase()
        response = sb.table("properties").select("*").execute()
        data = response.data or []
        if not data:
            return pd.DataFrame(columns=[
                "property_id", "property_name", "property_type", "location",
                "price", "bedrooms", "bathrooms", "area_sqft", "parking",
                "furnishing", "floor", "total_floors", "property_age",
                "possession", "amenities", "description", "availability",
                "broker_name", "broker_phone",
            ])
        df = pd.DataFrame(data)
        df["price"] = pd.to_numeric(df.get("price", 0), errors="coerce").fillna(0)
        df["bedrooms"] = pd.to_numeric(df.get("bedrooms", 0), errors="coerce").fillna(0).astype(int)
        df["bathrooms"] = pd.to_numeric(df.get("bathrooms", 0), errors="coerce").fillna(0).astype(int)
        df["area_sqft"] = pd.to_numeric(df.get("area_sqft", 0), errors="coerce").fillna(0).astype(int)
        if "broker_phone" not in df.columns:
            df["broker_phone"] = ""
        if "broker_name" not in df.columns:
            df["broker_name"] = ""
        return df
    except Exception as e:
        print(f"[Supabase] load_properties error: {e}")
        return pd.DataFrame(columns=[
            "property_id", "property_name", "property_type", "location",
            "price", "bedrooms", "bathrooms", "area_sqft", "parking",
            "furnishing", "floor", "total_floors", "property_age",
            "possession", "amenities", "description", "availability",
            "broker_name", "broker_phone",
        ])


# ── Buyers ────────────────────────────────────────────────────────────────────

def load_buyers() -> pd.DataFrame:
    """Load all buyers/leads from Supabase."""
    try:
        sb = get_supabase()
        response = sb.table("buyers").select("*").order("created_at", desc=True).execute()
        data = response.data or []
        if not data:
            return pd.DataFrame(columns=BUYERS_COLUMNS)
        return pd.DataFrame(data)
    except Exception as e:
        print(f"[Supabase] load_buyers error: {e}")
        return pd.DataFrame(columns=BUYERS_COLUMNS)


def generate_buyer_id(buyers_df: pd.DataFrame) -> str:
    """Generate the next sequential buyer ID."""
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
    """
    Upsert a buyer lead into Supabase.
    Matches on name (case-insensitive). Returns the buyer_id.
    """
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    name = buyer_state.get("name", "")
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

    amenities = buyer_state.get("amenities") or []
    if isinstance(amenities, list):
        amenities_str = ", ".join(amenities)
    else:
        amenities_str = str(amenities)

    buyer_row = {
        "name": name,
        "phone": buyer_state.get("phone", ""),
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

    try:
        sb = get_supabase()

        # Check if buyer already exists by name
        existing = sb.table("buyers").select("buyer_id").ilike("name", name).execute()

        if existing.data:
            buyer_id = existing.data[0]["buyer_id"]
            sb.table("buyers").update(buyer_row).eq("buyer_id", buyer_id).execute()
        else:
            # Generate next ID from current max
            all_buyers = sb.table("buyers").select("buyer_id").execute()
            df_ids = pd.DataFrame(all_buyers.data or [])
            buyer_id = generate_buyer_id(df_ids)
            buyer_row["buyer_id"] = buyer_id
            buyer_row["created_at"] = now
            sb.table("buyers").insert(buyer_row).execute()

        return buyer_id

    except Exception as e:
        print(f"[Supabase] save_buyer error: {e}")
        return "B000"


# ── Dashboard stats ───────────────────────────────────────────────────────────

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
