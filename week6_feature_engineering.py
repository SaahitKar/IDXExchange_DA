import os
import io
import warnings
import requests
import pandas as pd
import numpy as np
import geopandas as gpd

warnings.filterwarnings("ignore")

#Define Directory Paths
DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), "..", "Data Files")
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), "..", "Output Files")
OUTPUT_DIRECTORY_FILES = os.path.join(OUTPUT_DIRECTORY, "Modified Output Files")

os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
os.makedirs(OUTPUT_DIRECTORY_FILES, exist_ok=True)

input_path = os.path.join(OUTPUT_DIRECTORY_FILES, "Sold_Cleaned_Analysis_Ready.csv")
if not os.path.exists(input_path):
    input_path = os.path.join(OUTPUT_DIRECTORY, "sold.csv")

df = pd.read_csv(input_path, low_memory=False)

#Conduct Feature Engineering on DataFrame
date_cols = ["CloseDate", "ListingContractDate", "PurchaseContractDate"]
for col in date_cols:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

num_cols = ["ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea", "DaysOnMarket", "Latitude", "Longitude"]
for col in num_cols:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

#Engineer New Features
df["PriceRatio"] = np.where(
    (df["OriginalListPrice"].notnull()) & (df["OriginalListPrice"] > 0),
    df["ClosePrice"] / df["OriginalListPrice"],
    np.nan
)

df["PricePerSqFt"] = np.where(
    (df["LivingArea"].notnull()) & (df["LivingArea"] > 0),
    df["ClosePrice"] / df["LivingArea"],
    np.nan
)

df["CloseToOriginalListRatio"] = df["PriceRatio"]

if "CloseDate" in df.columns:
    df["Year"] = df["CloseDate"].dt.year
    df["Month"] = df["CloseDate"].dt.month
    df["YrMo"] = df["CloseDate"].dt.to_period("M").astype(str)

if "PurchaseContractDate" in df.columns and "ListingContractDate" in df.columns:
    df["ListingToContractDays"] = (df["PurchaseContractDate"] - df["ListingContractDate"]).dt.days

if "CloseDate" in df.columns and "PurchaseContractDate" in df.columns:
    df["ContractToCloseDays"] = (df["CloseDate"] - df["PurchaseContractDate"]).dt.days

school_district_geojson_url = "https://data.ca.gov/dataset/7dfaf005-58eb-45db-93b1-7aff091b2172/resource/7dfaf005-58eb-45db-93b1-7aff091b2172/download/california_school_district_areas_2024_25.geojson"

#Try to Assign School Districts to Properties
try:
    school_districts_gdf = gpd.read_file(school_district_geojson_url)
    
    valid_geo_mask = df["Latitude"].notnull() & df["Longitude"].notnull() & (df["Latitude"] != 0) & (df["Longitude"] != 0)
    valid_geo_df = df[valid_geo_mask].copy()

    #Create GeoDataFrame for Properties
    properties_gdf = gpd.GeoDataFrame(
        valid_geo_df,
        geometry=gpd.points_from_xy(valid_geo_df["Longitude"], valid_geo_df["Latitude"]),
        crs="EPSG:4326"
    )

    if school_districts_gdf.crs != properties_gdf.crs:
        school_districts_gdf = school_districts_gdf.to_crs(properties_gdf.crs)

    #Perform Join to Assign School Districts
    properties_with_district = gpd.sjoin(properties_gdf, school_districts_gdf, how="left", predicate="within")

    district_col = None
    possible_district_cols = ["DistrictName", "NAME", "District", "SchoolDistrict", "ELSDNAME", "UNSDNAME", "SCCSDNAME"]
    for col in possible_district_cols:
        if col in properties_with_district.columns:
            district_col = col
            break

    if district_col:
        df["SchoolDistrict"] = properties_with_district[district_col].reindex(df.index)
    else:
        df["SchoolDistrict"] = np.nan

except Exception as e:
    df["SchoolDistrict"] = np.nan

#Print Sample Output Table
print("Sample Output Table (Engineered Features):")
sample_columns = [
    "ClosePrice", "OriginalListPrice", "LivingArea", 
    "PriceRatio", "PricePerSqFt", "CloseToOriginalListRatio", 
    "YrMo", "ListingToContractDays", "ContractToCloseDays", "SchoolDistrict"
]
#Filter To Include Existing Columns Only
existing_sample_cols = [col for col in sample_columns if col in df.columns]
print(df[existing_sample_cols].head(10))

metrics = ["ClosePrice", "PriceRatio", "PricePerSqFt", "DaysOnMarket", "ListingToContractDays", "ContractToCloseDays"]
agg_dict = {}

#Aggregate Metrics
for metric in metrics:
    if metric in df.columns:
        agg_dict[metric] = ["count", "mean", "median", "std"]

segment_cols = ["PropertyType", "PropertySubType", "CountyOrParish", "MLSAreaMajor", "ListOfficeName", "BuyerOfficeName"]

#Generate Segmented Summary Tables
for seg_col in segment_cols:
    if seg_col in df.columns:
        grouped_summary = df.groupby(seg_col).agg(agg_dict)
        grouped_summary.columns = ['_'.join(col).strip() for col in grouped_summary.columns.values]
        grouped_summary = grouped_summary.reset_index()
        
        output_file_name = f"summary_segmented_by_{seg_col}.csv"
        grouped_summary.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, output_file_name), index=False)

        #Print Segmented Summary Table for Key Columns
        if seg_col in ["PropertyType", "CountyOrParish"]:
            print(f"\nSegmented Summary Table grouped by {seg_col}:")
            print(grouped_summary.head(10))

final_engineered_path = os.path.join(OUTPUT_DIRECTORY_FILES, "Sold_Engineered_Features.csv")
df.to_csv(final_engineered_path, index=False)
