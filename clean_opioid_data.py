import pandas as pd
import glob
import os

# ── 1. LOAD ALL YEARLY CSVs ──────────────────────────────────────────────────
# put all downloaded crime CSVs in the same folder as this script
csv_files = glob.glob("*.csv")
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
print(f"\ntotal rows before cleaning: {len(raw)}")

# ── 2. FILTER FOR NARCOTIC / OPIOID OFFENSES ────────────────────────────────
# these are the BPD offense codes related to drugs/narcotics
keep_offenses = [
    "DRUGS - POSSESSION OF DRUG PARAPHANALIA",
    "DRUGS - POSSESSION/ SALE/ MANUFACTURING/ USE",
    "SICK ASSIST - DRUG RELATED ILLNESS",
    "OPERATING UNDER THE INFLUENCE (OUI) DRUGS"
]
mask = raw["OFFENSE_DESCRIPTION"].str.upper().isin(
    [o.upper() for o in keep_offenses]
)
df = raw[mask].copy()
print(f"rows after narcotic filter: {len(df)}")

# ── 3. DROP ROWS MISSING CRITICAL COLUMNS ────────────────────────────────────
df = df.dropna(subset=["Lat", "Long", "OCCURRED_ON_DATE"])
df = df[df["Lat"] != 0]   # remove (0,0) placeholder coords
df = df[df["Long"] != 0]

# ── 4. PARSE DATETIME & CREATE DERIVED FEATURES ──────────────────────────────
df["OCCURRED_ON_DATE"] = pd.to_datetime(df["OCCURRED_ON_DATE"], format="mixed", utc=True).dt.tz_localize(None)
df["YEAR"]        = df["OCCURRED_ON_DATE"].dt.year
df["MONTH"]       = df["OCCURRED_ON_DATE"].dt.month
df["DAY_OF_WEEK"] = df["OCCURRED_ON_DATE"].dt.day_name()
df["HOUR"]        = df["OCCURRED_ON_DATE"].dt.hour
df["MONTH_YEAR"]  = df["OCCURRED_ON_DATE"].dt.to_period("M").astype(str)
df["SEASON"]      = df["MONTH"].map({
    12:"Winter", 1:"Winter", 2:"Winter",
    3:"Spring",  4:"Spring",  5:"Spring",
    6:"Summer",  7:"Summer",  8:"Summer",
    9:"Fall",   10:"Fall",   11:"Fall"
})
df["TIME_OF_DAY"] = pd.cut(
    df["HOUR"],
    bins=[-1, 5, 11, 17, 20, 23],
    labels=["Late Night", "Morning", "Afternoon", "Evening", "Night"]
)
df["IS_WEEKEND"] = df["DAY_OF_WEEK"].isin(["Saturday", "Sunday"]).astype(int)

# ── 5. MAP DISTRICT → NEIGHBORHOOD ───────────────────────────────────────────
district_to_neighborhood = {
    "A1":  "Downtown/Beacon Hill",
    "A15": "Charlestown",
    "A7":  "East Boston",
    "B2":  "Roxbury",
    "B3":  "Mattapan",
    "C6":  "South Boston",
    "C11": "Dorchester",
    "D4":  "South End/Fenway",
    "D14": "Brighton/Allston",
    "E5":  "West Roxbury",
    "E13": "Jamaica Plain",
    "E18": "Hyde Park",
}
df["NEIGHBORHOOD"] = df["DISTRICT"].map(district_to_neighborhood).fillna("Unknown")

# ── 6. CLEAN UP COLUMNS ───────────────────────────────────────────────────────
df = df[[
    "INCIDENT_NUMBER", "OFFENSE_CODE", "OFFENSE_DESCRIPTION",
    "DISTRICT", "NEIGHBORHOOD", "STREET",
    "OCCURRED_ON_DATE", "YEAR", "MONTH", "MONTH_YEAR",
    "DAY_OF_WEEK", "HOUR", "TIME_OF_DAY", "SEASON", "IS_WEEKEND",
    "Lat", "Long"
]]

df = df.drop_duplicates(subset="INCIDENT_NUMBER")
df = df.reset_index(drop=True)

# ── 7. FINAL SUMMARY ─────────────────────────────────────────────────────────
print(f"\nfinal clean rows: {len(df)}")
print(f"columns ({len(df.columns)}): {list(df.columns)}")
print(f"years covered: {sorted(df['YEAR'].unique())}")
print(f"\nincidents by neighborhood:\n{df['NEIGHBORHOOD'].value_counts()}")
print(f"\nincidents by year:\n{df['YEAR'].value_counts().sort_index()}")

# ── 8. SAVE ───────────────────────────────────────────────────────────────────
df.to_csv("opioid_incidents_clean.csv", index=False)
print("\nsaved → opioid_incidents_clean.csv")