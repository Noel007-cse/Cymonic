import pandas as pd
from typing import Optional, List

# Configurable weights (sum = 100)
WEIGHTS = {
    "budget": 28,
    "location": 22,
    "property_type": 13,
    "bedrooms": 12,
    "timeline": 8,
    "parking": 4,
    "amenities": 8,
    "size": 5,
}

# Location proximity groups
LOCATION_GROUPS = {
    "kochi_central": ["Ernakulam", "Kochi", "MG Road", "Palarivattom", "Edappally", "Vyttila",
                      "Thripunithura", "Thrippunithura", "Maradu"],
    "kochi_north": ["Kakkanad", "Kalamassery", "Aluva", "Angamaly", "Perumbavoor"],
    "thrissur_district": ["Thrissur", "Chalakudy", "Irinjalakuda"],
    "trivandrum_district": ["Trivandrum", "Thiruvananthapuram", "Kazhakkoottam", "Technopark"],
    "calicut_district": ["Calicut", "Kozhikode", "Nadakkavu", "Palayam"],
    "central_kerala": ["Kottayam", "Vaikom", "Pathanamthitta", "Changanacherry", "Pala"],
    "palakkad_district": ["Palakkad", "Ottapalam", "Shoranur"],
}


def get_location_group(location: str) -> Optional[str]:
    if not location:
        return None
    loc_lower = location.strip().lower()
    for group, locs in LOCATION_GROUPS.items():
        for l in locs:
            if l.lower() == loc_lower:
                return group
    return None


def score_budget(buyer_max: float, buyer_min: Optional[float], property_price: float) -> float:
    """Score budget compatibility (0-28)."""
    if not buyer_max or buyer_max <= 0:
        return 14
    if not buyer_min:
        buyer_min = buyer_max * 0.7
    if buyer_min <= property_price <= buyer_max:
        return 28
    if property_price < buyer_min:
        ratio = property_price / buyer_min
        return 26 if ratio >= 0.7 else 18
    overage = (property_price - buyer_max) / buyer_max
    if overage <= 0.05:
        return 22
    elif overage <= 0.10:
        return 16
    elif overage <= 0.20:
        return 9
    elif overage <= 0.30:
        return 4
    return 0


def score_location(buyer_location: str, property_location: str) -> float:
    """Score location match (0-22)."""
    if not buyer_location or not property_location:
        return 9
    buyer_loc = buyer_location.strip().lower()
    prop_loc = property_location.strip().lower()
    if buyer_loc == prop_loc:
        return 22
    buyer_group = get_location_group(buyer_location)
    prop_group = get_location_group(property_location)
    if buyer_group and prop_group and buyer_group == prop_group:
        return 14
    if buyer_loc in prop_loc or prop_loc in buyer_loc:
        return 18
    return 0


def score_property_type(buyer_type: str, property_type: str) -> float:
    """Score property type match (0-13)."""
    if not buyer_type or not property_type:
        return 6
    type_map = {
        "flat": "apartment",
        "condo": "apartment",
        "house": "independent house",
    }
    buyer_t = type_map.get(buyer_type.strip().lower(), buyer_type.strip().lower())
    prop_t = type_map.get(property_type.strip().lower(), property_type.strip().lower())
    if buyer_t == prop_t:
        return 13
    semi = [{"apartment", "studio"}, {"villa", "independent house"}, {"row house", "independent house"}]
    for group in semi:
        if {buyer_t} & group and {prop_t} & group:
            return 7
    return 0


def score_bedrooms(buyer_bedrooms, property_bedrooms) -> float:
    """Score bedroom match (0-12)."""
    if not buyer_bedrooms or not property_bedrooms:
        return 6
    diff = abs(int(buyer_bedrooms) - int(property_bedrooms))
    if diff == 0:
        return 12
    elif diff == 1:
        return 7
    elif diff == 2:
        return 3
    return 0


def score_timeline(timeline_days, possession: str) -> float:
    """Score timeline vs possession (0-8)."""
    if not timeline_days:
        return 4
    if not possession:
        return 4
    p = possession.strip().lower()
    if p == "ready":
        return 8
    elif "6 month" in p:
        return 8 if timeline_days >= 180 else (6 if timeline_days >= 120 else 2)
    elif "1 year" in p or "12 month" in p:
        return 8 if timeline_days >= 365 else (4 if timeline_days >= 180 else 0)
    elif "under construction" in p:
        return 5 if timeline_days >= 365 else 1
    return 4


def score_parking(buyer_parking, property_parking: str) -> float:
    """Score parking (0-4)."""
    has_parking = str(property_parking).strip().lower() in ["yes", "true", "1"]
    if buyer_parking is None or buyer_parking == "":
        return 2
    buyer_p = str(buyer_parking).strip().lower()
    if buyer_p == "yes" and has_parking:
        return 4
    if buyer_p == "no":
        return 4
    if buyer_p == "preferable":
        return 4 if has_parking else 2
    if buyer_p == "yes" and not has_parking:
        return 0
    return 2


def score_amenities(buyer_amenities, property_amenities_str: str) -> float:
    """Score amenity overlap (0-8)."""
    if not buyer_amenities:
        return 4
    if isinstance(buyer_amenities, str):
        try:
            import json
            buyer_list = json.loads(buyer_amenities)
        except Exception:
            buyer_list = [a.strip().lower() for a in buyer_amenities.split(",") if a.strip()]
    else:
        buyer_list = [str(a).strip().lower() for a in buyer_amenities]

    if not buyer_list:
        return 4

    prop_amenities_lower = property_amenities_str.lower() if property_amenities_str else ""
    matched = sum(1 for amenity in buyer_list if amenity in prop_amenities_lower)
    ratio = matched / len(buyer_list)
    return round(8 * ratio, 1)


def score_size(buyer_min_sqft, buyer_max_sqft, property_sqft: int) -> float:
    """Score property size compatibility (0-5)."""
    prop = int(property_sqft) if property_sqft else 0
    bmin = int(buyer_min_sqft) if buyer_min_sqft else 0
    bmax = int(buyer_max_sqft) if buyer_max_sqft else 0
    if bmin == 0 and bmax == 0:
        return 2.5  # Not specified
    if bmax == 0:
        bmax = bmin * 1.5
    if bmin == 0:
        bmin = bmax * 0.6
    if bmin <= prop <= bmax:
        return 5
    overage = abs(prop - bmax) / bmax if prop > bmax else abs(bmin - prop) / bmin
    if overage <= 0.10:
        return 4
    elif overage <= 0.20:
        return 3
    elif overage <= 0.30:
        return 1
    return 0


def generate_match_explanation(buyer_state: dict, row: pd.Series) -> dict:
    positives = []
    negatives = []
    budget_max = buyer_state.get("budget_max", 0) or 0
    price = float(row["price"])
    if budget_max > 0:
        if price <= budget_max:
            positives.append(f"Budget fits (Rs{price/100000:.0f}L <= Rs{budget_max/100000:.0f}L)")
        elif (price - budget_max) / budget_max <= 0.10:
            negatives.append(f"Price is Rs{(price-budget_max)/100000:.1f}L above budget (within 10%)")
        else:
            negatives.append(f"Price Rs{price/100000:.0f}L exceeds budget Rs{budget_max/100000:.0f}L")
    buyer_loc = (buyer_state.get("location") or "").strip().lower()
    prop_loc = str(row["location"]).strip().lower()
    if buyer_loc == prop_loc:
        positives.append("Exact location match")
    elif get_location_group(buyer_state.get("location", "")) == get_location_group(str(row["location"])) and get_location_group(str(row["location"])):
        positives.append("Nearby location (same area)")
    else:
        negatives.append("Different location")
    buyer_beds = buyer_state.get("bedrooms")
    prop_beds = row.get("bedrooms")
    if buyer_beds and prop_beds:
        if int(buyer_beds) == int(prop_beds):
            positives.append(f"Exact {buyer_beds}BHK match")
        else:
            negatives.append(f"Property has {prop_beds}BHK (you wanted {buyer_beds}BHK)")
    # Parking
    parking_val = str(row.get("parking", "")).lower()
    buyer_p = str(buyer_state.get("parking", "") or "").lower()
    if parking_val == "yes":
        positives.append("Parking available")
    elif buyer_p == "yes":
        negatives.append("No parking available")
    # Possession
    possession = str(row.get("possession", ""))
    if possession.lower() == "ready":
        positives.append("Available immediately")
    elif possession:
        positives.append(f"Possession: {possession}")
    # Amenities match
    buyer_amenities = buyer_state.get("amenities") or []
    prop_amenities_str = str(row.get("amenities", ""))
    if isinstance(buyer_amenities, list) and buyer_amenities:
        matched_a = [a for a in buyer_amenities if a.lower() in prop_amenities_str.lower()]
        missing_a = [a for a in buyer_amenities if a.lower() not in prop_amenities_str.lower()]
        if matched_a:
            positives.append(f"Amenities matched: {', '.join(matched_a)}")
        if missing_a:
            negatives.append(f"Missing amenities: {', '.join(missing_a)}")
    return {"positives": positives, "negatives": negatives}


def match_properties(buyer_state: dict, properties_df: pd.DataFrame, top_n: int = 10) -> list:
    """Match buyer requirements against available properties. Returns top N sorted by score."""
    available = properties_df[properties_df["availability"].str.lower() == "available"].copy()
    if available.empty:
        return []
    results = []
    buyer_max = buyer_state.get("budget_max") or 0
    buyer_min = buyer_state.get("budget_min")
    buyer_location = buyer_state.get("location", "")
    buyer_type = buyer_state.get("property_type", "")
    buyer_beds = buyer_state.get("bedrooms")
    buyer_timeline = buyer_state.get("timeline_days")
    buyer_parking = buyer_state.get("parking")
    buyer_amenities = buyer_state.get("amenities")
    buyer_size_min = buyer_state.get("size_min_sqft")
    buyer_size_max = buyer_state.get("size_max_sqft")
    for _, row in available.iterrows():
        b_score  = score_budget(buyer_max, buyer_min, float(row["price"]))
        l_score  = score_location(buyer_location, str(row["location"]))
        t_score  = score_property_type(buyer_type, str(row["property_type"]))
        bed_score = score_bedrooms(buyer_beds, row.get("bedrooms", 0))
        time_score = score_timeline(buyer_timeline, str(row.get("possession", "Ready")))
        p_score  = score_parking(buyer_parking, str(row.get("parking", "No")))
        a_score  = score_amenities(buyer_amenities, str(row.get("amenities", "")))
        sz_score = score_size(buyer_size_min, buyer_size_max, int(row.get("area_sqft", 0)))
        total = b_score + l_score + t_score + bed_score + time_score + p_score + a_score + sz_score
        explanation = generate_match_explanation(buyer_state, row)
        results.append({
            "property_id": row["property_id"],
            "property_name": row["property_name"],
            "property_type": row["property_type"],
            "location": row["location"],
            "price": float(row["price"]),
            "bedrooms": int(row.get("bedrooms", 0)),
            "bathrooms": int(row.get("bathrooms", 0)),
            "area_sqft": int(row.get("area_sqft", 0)),
            "parking": str(row.get("parking", "No")),
            "furnishing": str(row.get("furnishing", "")),
            "possession": str(row.get("possession", "")),
            "amenities": str(row.get("amenities", "")),
            "description": str(row.get("description", "")),
            "broker_phone": str(row.get("broker_phone", "")),
            "broker_name": str(row.get("broker_name", "")),
            "match_score": round(total, 1),
            "explanation": explanation,
        })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_n]
