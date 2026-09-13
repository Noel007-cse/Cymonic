"""
seed_supabase.py -- Migrate CSV data to Supabase
Run once: python seed_supabase.py
"""
import sys
import os
import pandas as pd
from dotenv import load_dotenv

# Fix Windows console encoding
sys.stdout.reconfigure(encoding="utf-8")

# Load env from project root
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
load_dotenv(env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
# Use service role key for seeding (bypasses RLS)
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
    sys.exit(1)

from supabase import create_client
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")

# ── Seed properties ───────────────────────────────────────────────────────────
props_csv = os.path.join(DATA_DIR, "properties.csv")
if os.path.exists(props_csv):
    df = pd.read_csv(props_csv)
    df.columns = df.columns.str.strip()
    df["price"]        = pd.to_numeric(df["price"], errors="coerce").fillna(0).astype(int)
    df["bedrooms"]     = pd.to_numeric(df["bedrooms"], errors="coerce").fillna(0).astype(int)
    df["bathrooms"]    = pd.to_numeric(df["bathrooms"], errors="coerce").fillna(0).astype(int)
    df["area_sqft"]    = pd.to_numeric(df["area_sqft"], errors="coerce").fillna(0).astype(int)
    df["floor"]        = pd.to_numeric(df.get("floor", 0), errors="coerce").fillna(0).astype(int)
    df["total_floors"] = pd.to_numeric(df.get("total_floors", 0), errors="coerce").fillna(0).astype(int)
    df["property_age"] = pd.to_numeric(df.get("property_age", 0), errors="coerce").fillna(0).astype(int)
    df = df.fillna("")

    records = df.to_dict(orient="records")
    print(f"Seeding {len(records)} properties...")

    BATCH = 50
    for i in range(0, len(records), BATCH):
        batch = records[i : i + BATCH]
        sb.table("properties").upsert(batch, on_conflict="property_id").execute()
        print(f"  Inserted rows {i+1}-{min(i+BATCH, len(records))}")

    print(f"Properties done ({len(records)} rows)\n")
else:
    print(f"WARNING: {props_csv} not found -- skipping properties seed")

# ── Seed buyers ───────────────────────────────────────────────────────────────
buyers_csv = os.path.join(DATA_DIR, "buyers.csv")
if os.path.exists(buyers_csv):
    df = pd.read_csv(buyers_csv)
    df.columns = df.columns.str.strip()

    int_cols   = ["budget", "budget_min", "budget_max", "bedrooms",
                  "timeline_days", "qualification_score",
                  "size_min_sqft", "size_max_sqft"]
    float_cols = ["best_match_score"]

    for c in int_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    for c in float_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    df = df.fillna("")
    records = df.to_dict(orient="records")
    print(f"Seeding {len(records)} buyers...")

    sb.table("buyers").upsert(records, on_conflict="buyer_id").execute()
    print(f"Buyers done ({len(records)} rows)\n")
else:
    print(f"WARNING: {buyers_csv} not found -- skipping buyers seed")

print("Migration complete! Your Supabase project is ready.")
