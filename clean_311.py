import pandas as pd
import glob

# ── 1. LOAD ALL 311 CSVs ──────────────────────────────────────────────────────
csv_files = list(set(glob.glob("311_*.csv") + glob.glob("311_*.csv.csv")))
print(f"found files: {csv_files}")

dfs = []
for f in csv_files:
    try:
        df = pd.read_csv(f, encoding="utf-8", low_memory=False)
        print(f"  loaded {f}: {len(df)} rows")
        dfs.append(df)
    except Exception as e:
        print(f"  skipped {f}: {e}")

raw = pd.concat(dfs, ignore_index=True)
print(f"\ntotal rows before filtering: {len(raw)}")

# ── 2. FILTER FOR NEEDLE/SYRINGE REQUESTS USING 'type' COLUMN ────────────────
needle_keywords = ["NEEDLE", "SYRINGE", "SHARP", "DRUG PARAPHERNALIA"]

mask = raw["type"].str.upper().str.contains(
    "|".join(needle_keywords), na=False
)
df = raw[mask].copy()
print(f"rows after needle filter: {len(df)}")
print(f"\nneedle request types found:\n{df['type'].value_counts().head(20)}")
print(f"\nsubject breakdown:\n{df['subject'].value_counts().head(10)}")

# ── 3. PARSE DATES & DERIVE FEATURES ─────────────────────────────────────────
df["open_dt"] = pd.to_datetime(df["open_dt"], format="mixed", utc=True).dt.tz_localize(None)
df["YEAR"]        = df["open_dt"].dt.year
df["MONTH"]       = df["open_dt"].dt.month
df["MONTH_YEAR"]  = df["open_dt"].dt.to_period("M").astype(str)
df["DAY_OF_WEEK"] = df["open_dt"].dt.day_name()
df["HOUR"]        = df["open_dt"].dt.hour
df["SEASON"]      = df["MONTH"].map({
    12:"Winter", 1:"Winter", 2:"Winter",
    3:"Spring",  4:"Spring",  5:"Spring",
    6:"Summer",  7:"Summer",  8:"Summer",
    9:"Fall",   10:"Fall",   11:"Fall"
})

# ── 4. CLEAN UP COLUMNS ───────────────────────────────────────────────────────
df = df[[
    "case_enquiry_id", "type", "subject", "reason",
    "open_dt", "closed_dt", "on_time", "case_status",
    "YEAR", "MONTH", "MONTH_YEAR", "DAY_OF_WEEK", "HOUR", "SEASON",
    "neighborhood", "location_street_name", "location_zipcode",
    "latitude", "longitude", "police_district"
]]

# drop missing coords and neighborhood
df = df.dropna(subset=["latitude", "longitude", "neighborhood"])
df = df[df["latitude"] != 0]
df = df[df["YEAR"] <= 2024]  # drop partial 2025 data
df = df.reset_index(drop=True)

# ── 5. SUMMARY ────────────────────────────────────────────────────────────────
print(f"\nfinal clean rows: {len(df)}")
print(f"years covered: {sorted(df['YEAR'].unique())}")
print(f"\nrequests by neighborhood:\n{df['neighborhood'].value_counts().head(15)}")
print(f"\nrequests by year:\n{df['YEAR'].value_counts().sort_index()}")

# ── 6. SAVE ───────────────────────────────────────────────────────────────────
df.to_csv("needle_requests_clean.csv", index=False)
print("\nsaved → needle_requests_clean.csv")