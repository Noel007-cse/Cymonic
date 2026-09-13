import pandas as pd
from typing import Optional

# Configurable weights (sum = 100)
WEIGHTS = {
    "budget": 30,
    "location": 25,
    "property_type": 15,
    "bedrooms": 15,
    "timeline": 10,
    "parking": 5,
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
    """Score budget compatibility (0-30)."""
    if not buyer_max or buyer_max <= 0:
        return 15
    if not buyer_min:
        buyer_min = buyer_max * 0.7
    if buyer_min <= property_price <= buyer_max:
        return 30
    if property_price < buyer_min:
        ratio = property_price / buyer_min
        return 28 if ratio >= 0.7 else 20
    overage = (property_price - buyer_max) / buyer_max
    if overage <= 0.05:
        return 24
    elif overage <= 0.10:
        return 18
    elif overage <= 0.20:
        return 10
    elif overage <= 0.30:
        return 5
    return 0


def score_location(buyer_location: str, property_location: str) -> float:
    """Score location match (0-25)."""
    if not buyer_location or not property_location:
        return 10
    buyer_loc = buyer_location.strip().lower()
    prop_loc = property_location.strip().lower()
    if buyer_loc == prop_loc:
        return 25
    buyer_group = get_location_group(buyer_location)
    prop_group = get_location_group(property_location)
    if buyer_group and prop_group and buyer_group == prop_group:
        return 15
    if buyer_loc in prop_loc or prop_loc in buyer_loc:
        return 20
    return 0


def score_property_type(buyer_type: str, property_type: str) -> float:
    """Score property type match (0-15)."""
    if not buyer_type or not property_type:
        return 7
    type_map = {
        "flat": "apartment",
        "condo": "apartment",
        "house": "independent house",
    }
    buyer_t = type_map.get(buyer_type.strip().lower(), buyer_type.strip().lower())
    prop_t = type_map.get(property_type.strip().lower(), property_type.strip().lower())
    if buyer_t == prop_t:
        return 15
    semi = [{"apartment", "studio"}, {"villa", "independent house"}, {"row house", "independent house"}]
    for group in semi:
        if {buyer_t} & group and {prop_t} & group:
            return 8
    return 0


def score_bedrooms(buyer_bedrooms, property_bedrooms) -> float:
    """Score bedroom match (0-15)."""
    if not buyer_bedrooms or not property_bedrooms:
        return 7
    diff = abs(int(buyer_bedrooms) - int(property_bedrooms))
    if diff == 0:
        return 15
    elif diff == 1:
        return 8
    elif diff == 2:
        return 3
    return 0


def score_timeline(timeline_days, possession: str) -> float:
    """Score timeline vs possession (0-10)."""
    if not timeline_days:
        return 5
    if not possession:
        return 5
    p = possession.strip().lower()
    if p == "ready":
        return 10
    elif "6 month" in p:
        return 10 if timeline_days >= 180 else (7 if timeline_days >= 120 else 3)
    elif "1 year" in p or "12 month" in p:
        return 10 if timeline_days >= 365 else (5 if timeline_days >= 180 else 0)
    elif "under construction" in p:
        return 6 if timeline_days >= 365 else 1
    return 5


def score_parking(buyer_parking, property_parking: str) -> float:
    """Score parking (0-5)."""
    has_parking = str(property_parking).strip().lower() in ["yes", "true", "1"]
    if buyer_parking is None:
        return 3
    if buyer_parking and has_parking:
        return 5
    if not buyer_parking:
        return 5
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
    if str(row.get("parking", "")).lower() == "yes":
        positives.append("Parking available")
    possession = str(row.get("possession", ""))
    if possession.lower() == "ready":
        positives.append("Available immediately")
    elif possession:
        positives.append(f"Possession: {possession}")
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
    for _, row in available.iterrows():
        b_score = score_budget(buyer_max, buyer_min, float(row["price"]))
        l_score = score_location(buyer_location, str(row["location"]))
        t_score = score_property_type(buyer_type, str(row["property_type"]))
        bed_score = score_bedrooms(buyer_beds, row.get("bedrooms", 0))
        time_score = score_timeline(buyer_timeline, str(row.get("possession", "Ready")))
        p_score = score_parking(buyer_parking, str(row.get("parking", "No")))
        total = b_score + l_score + t_score + bed_score + time_score + p_score
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
            "match_score": round(total, 1),
            "explanation": explanation,
        })
    results.sort(key=lambda x: x["match_score"], reverse=True)
    return results[:top_n]
