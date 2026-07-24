import os
import io
import warnings
import pandas as pd
import numpy as np
import requests

warnings.filterwarnings("ignore")

# Define Directory Paths
DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "..", "Data Files")
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), "..", "Output Files")
OUTPUT_DIRECTORY_FILES = os.path.join(OUTPUT_DIRECTORY, "Modified Output Files")

os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
os.makedirs(OUTPUT_DIRECTORY_FILES, exist_ok=True)


# 1. Fetch MORTGAGE30US series directly from FRED
fred_url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
response = requests.get(fred_url, verify=False)
if response.status_code != 200:
    raise RuntimeError(f"Failed to fetch FRED data. Status code: {response.status_code}")

mortgage_df = pd.read_csv(io.StringIO(response.text))
mortgage_df.columns = ["date", "rate_30yr_fixed"]
mortgage_df["date"] = pd.to_datetime(mortgage_df["date"], errors="coerce")
mortgage_df["rate_30yr_fixed"] = pd.to_numeric(mortgage_df["rate_30yr_fixed"], errors="coerce")

# 2. Resample MORTGAGE30US to monthly averages
mortgage_df["year_month"] = mortgage_df["date"].dt.to_period("M")
mortgage_monthly = (
    mortgage_df.groupby("year_month")["rate_30yr_fixed"]
    .mean()
    .reset_index()
)

# Load Sold and Listings Datasets
sold_path = os.path.join(OUTPUT_DIRECTORY, "sold.csv")
listings_path = os.path.join(OUTPUT_DIRECTORY_FILES, "listings.csv")

if not os.path.exists(listings_path):
    listings_path = os.path.join(OUTPUT_DIRECTORY, "listings.csv")

sold = pd.read_csv(sold_path, low_memory=False)
listings = pd.read_csv(listings_path, low_memory=False)

# Prepare year_month keys
sold["CloseDate_dt"] = pd.to_datetime(sold["CloseDate"], errors="coerce")
sold["year_month"] = sold["CloseDate_dt"].dt.to_period("M")

listings["ListingContractDate_dt"] = pd.to_datetime(listings["ListingContractDate"], errors="coerce")
listings["year_month"] = listings["ListingContractDate_dt"].dt.to_period("M")

# Drop temp date columns before merge
sold = sold.drop(columns=["CloseDate_dt"])
listings = listings.drop(columns=["ListingContractDate_dt"])

# 3. Merge onto both datasets
sold_enriched = sold.merge(mortgage_monthly, on="year_month", how="left")
listings_enriched = listings.merge(mortgage_monthly, on="year_month", how="left")

# 4. Validation Checks & Null Handling
sold_nulls = sold_enriched["rate_30yr_fixed"].isnull().sum()
listings_nulls = listings_enriched["rate_30yr_fixed"].isnull().sum()

# Handle Nulls if missing dates exist outside the FRED range
if sold_nulls > 0:
    sold_enriched["rate_30yr_fixed"] = sold_enriched["rate_30yr_fixed"].ffill().bfill()
if listings_nulls > 0:
    listings_enriched["rate_30yr_fixed"] = listings_enriched["rate_30yr_fixed"].ffill().bfill()


# Save Enriched Datasets
sold_enriched.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "CombinedSold_Validated.csv"), index=False)
listings_enriched.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "CombinedListings_Enriched.csv"), index=False)

# Use enriched sold dataset for main cleaning pipeline
df = sold_enriched.copy()
initial_row_count = len(df)
print(f"Initial Row Count: {initial_row_count}")

# 1. Convert Date Fields to Datetime
date_fields = [
    "CloseDate",
    "PurchaseContractDate",
    "ListingContractDate",
    "ContractStatusChangeDate"
]

for d_col in date_fields:
    if d_col in df.columns:
        df[d_col] = pd.to_datetime(df[d_col], errors="coerce")

print("\nData Types Confirmation (Date Fields):")
print(df[date_fields].dtypes)

# 2. Convert Numeric Fields and Handle Missing/Type Formatting
numeric_fields = [
    "ClosePrice",
    "ListPrice",
    "OriginalListPrice",
    "LivingArea",
    "LotSizeAcres",
    "BedroomsTotal",
    "BathroomsTotalInteger",
    "DaysOnMarket",
    "YearBuilt",
    "Latitude",
    "Longitude"
]

for n_col in numeric_fields:
    if n_col in df.columns:
        df[n_col] = pd.to_numeric(df[n_col], errors="coerce")

# Remove or flag invalid numeric values
print("\nCleaning Invalid Numeric Values...")

# Flagging invalid numeric values
df["invalid_numeric_flag"] = False

if "ClosePrice" in df.columns:
    df["invalid_numeric_flag"] |= df["ClosePrice"] <= 0
if "LivingArea" in df.columns:
    df["invalid_numeric_flag"] |= df["LivingArea"] <= 0
if "DaysOnMarket" in df.columns:
    df["invalid_numeric_flag"] |= df["DaysOnMarket"] < 0
if "BedroomsTotal" in df.columns:
    df["invalid_numeric_flag"] |= df["BedroomsTotal"] < 0
if "BathroomsTotalInteger" in df.columns:
    df["invalid_numeric_flag"] |= df["BathroomsTotalInteger"] < 0

print(f"Records with invalid numeric values flagged: {df['invalid_numeric_flag'].sum()}")

# Filtering out records with invalid non-positive prices/living areas
df_clean = df[
    (df["ClosePrice"] > 0) & 
    (df["LivingArea"] > 0) & 
    (df["DaysOnMarket"] >= 0)
].copy()

# 3. Date Consistency Checks

if "ListingContractDate" in df_clean.columns and "CloseDate" in df_clean.columns:
    df_clean["listing_after_close_flag"] = df_clean["ListingContractDate"] > df_clean["CloseDate"]
else:
    df_clean["listing_after_close_flag"] = False

if "PurchaseContractDate" in df_clean.columns and "CloseDate" in df_clean.columns:
    df_clean["purchase_after_close_flag"] = df_clean["PurchaseContractDate"] > df_clean["CloseDate"]
else:
    df_clean["purchase_after_close_flag"] = False

if "ListingContractDate" in df_clean.columns and "PurchaseContractDate" in df_clean.columns:
    df_clean["negative_timeline_flag"] = df_clean["PurchaseContractDate"] < df_clean["ListingContractDate"]
else:
    df_clean["negative_timeline_flag"] = False

print(f"Listing After Close Violations: {df_clean['listing_after_close_flag'].sum()}")
print(f"Purchase After Close Violations: {df_clean['purchase_after_close_flag'].sum()}")
print(f"Negative Timeline Violations (Purchase before Listing): {df_clean['negative_timeline_flag'].sum()}")

# 4. Geographic Data Checks

if "Latitude" in df_clean.columns and "Longitude" in df_clean.columns:
    # Missing Coordinates
    df_clean["geo_missing_flag"] = df_clean["Latitude"].isnull() | df_clean["Longitude"].isnull()
    
    # Sentinel Zero Values
    df_clean["geo_zero_flag"] = (df_clean["Latitude"] == 0) | (df_clean["Longitude"] == 0)
    
    # Longitude > 0 Error (CA coordinates must be negative)
    df_clean["geo_positive_longitude_flag"] = df_clean["Longitude"] > 0
    
    # Out of State / Implausible Coordinates for California
    # CA Approx Boundaries: Lat 32.5 to 42.0, Long -124.5 to -114.1
    df_clean["geo_out_of_bounds_flag"] = ~(
        df_clean["Latitude"].between(32.5, 42.0) & 
        df_clean["Longitude"].between(-124.5, -114.1)
    ) & ~df_clean["geo_missing_flag"] & ~df_clean["geo_zero_flag"]

    print(f"Missing Coordinates Count: {df_clean['geo_missing_flag'].sum()}")
    print(f"Sentinel Zero Coordinates Count: {df_clean['geo_zero_flag'].sum()}")
    print(f"Positive Longitude Error Count: {df_clean['geo_positive_longitude_flag'].sum()}")
    print(f"Out of State / Implausible CA Coordinates Count: {df_clean['geo_out_of_bounds_flag'].sum()}")

# 5. Remove Redundant Columns
cols_to_drop = ["year_month"]
df_clean = df_clean.drop(columns=[c for c in cols_to_drop if c in df_clean.columns])

final_row_count = len(df_clean)

print("\nFINAL SUMMARY REPORT: ")
print(f"Before Row Count: {initial_row_count}")
print(f"After Row Count:  {final_row_count}")
print(f"Total Rows Removed (Invalid Numeric Filters): {initial_row_count - final_row_count}")

# Save Cleaned Dataset
cleaned_output_path = os.path.join(OUTPUT_DIRECTORY_FILES, "Sold_Cleaned_Analysis_Ready.csv")
df_clean.to_csv(cleaned_output_path, index=False)
print(f"\nCleaned analysis-ready dataset saved to:\n{cleaned_output_path}")