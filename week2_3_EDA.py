import os
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Data Files')
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Output Files')
OUTPUT_DIRECTORY_FILES = os.path.join(OUTPUT_DIRECTORY, 'Modified Output Files')

os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
os.makedirs(OUTPUT_DIRECTORY_FILES, exist_ok=True)

output_path = os.path.join(OUTPUT_DIRECTORY, 'sold.csv')
sold = pd.read_csv(output_path, low_memory=False)

print("Dataset Shape: ", sold.shape)
print("\nColumn Data Types:")
print(sold.dtypes)

print("Number of Unique Property Types: ", sold["PropertyType"].nunique())
print("\nProperty Types:")
print(sold["PropertyType"].value_counts(dropna=False))

sold = sold[sold["PropertyType"] == "Residential"]

missing_values = pd.DataFrame({
    "Missing Count": sold.isnull().sum(),
    "Missing Percent": sold.isnull().mean() * 100
})
missing_values = missing_values.sort_values(by="Missing Percent", ascending=False)

print("\nMissing Value Report:")
print(missing_values)

high_missing = missing_values[missing_values["Missing Percent"] > 90]
print("\nColumns with More than 90% Missing Values:")
print(f"{high_missing}\n")

core_fields = [
    "ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea", 
    "LotSizeAcres", "BedroomsTotal", "BathroomsTotalInteger", 
    "DaysOnMarket", "YearBuilt", "CloseDate", "ListingContractDate", "CountyOrParish"
]
columns_to_drop = [col for col in high_missing.index if col not in core_fields]
sold = sold.drop(columns=columns_to_drop)

missing_values.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "missing_value_report.csv"), index=True)
high_missing.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "high_missing_columns_over_90.csv"), index=True)

numeric_columns = [
    "ClosePrice", "ListPrice", "OriginalListPrice", "LivingArea", 
    "LotSizeAcres", "BedroomsTotal", "BathroomsTotalInteger", 
    "DaysOnMarket", "YearBuilt"
]

for col in numeric_columns:
    if col in sold.columns:
        sold[col] = pd.to_numeric(sold[col], errors="coerce")

distribution_summary = sold[numeric_columns].describe(
    percentiles=[0.01, 0.05, 0.25, 0.50, 0.75, 0.95, 0.99]
)
print("\nNumerical Columns Summary:")
print(distribution_summary)
distribution_summary.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "numeric_distribution_summary.csv"), index=True)


OUTPUT_DIRECTORY_CHARTS = os.path.join(OUTPUT_DIRECTORY, 'Charts')
os.makedirs(OUTPUT_DIRECTORY_CHARTS, exist_ok=True)

for col in numeric_columns:
    if col in sold.columns:
        plt.figure()
        sold[col].dropna().hist(bins=40)
        plt.title(f"Histogram of {col}")
        plt.xlabel(col)
        plt.ylabel("Frequency")
        plt.savefig(os.path.join(OUTPUT_DIRECTORY_CHARTS, f"{col}_histogram.png"))
        plt.close()

        plt.figure()
        sold.boxplot(column=col)
        plt.title(f"Boxplot of {col}")
        plt.ylabel(col)
        plt.savefig(os.path.join(OUTPUT_DIRECTORY_CHARTS, f"{col}_boxplot.png"))
        plt.close()

print("\nClosePrice average:", sold["ClosePrice"].mean())
print("ClosePrice median:", sold["ClosePrice"].median())

print("\nDaysOnMarket summary:")
print(sold["DaysOnMarket"].describe())

if "ListPrice" in sold.columns:
    valid_prices = sold.dropna(subset=["ClosePrice", "ListPrice"])
    above_list = (valid_prices["ClosePrice"] > valid_prices["ListPrice"]).mean() * 100
    below_list = (valid_prices["ClosePrice"] < valid_prices["ListPrice"]).mean() * 100
    at_list = (valid_prices["ClosePrice"] == valid_prices["ListPrice"]).mean() * 100

    print("\nPercentage of Homes Sold Above List Price:", above_list)
    print("Percentage of Homes Sold Below List Price:", below_list)
    print("Percentage of Homes Sold at List Price:", at_list)

if "CloseDate" in sold.columns and "ListingContractDate" in sold.columns:
    sold["CloseDate"] = pd.to_datetime(sold["CloseDate"], errors="coerce")
    sold["ListingContractDate"] = pd.to_datetime(sold["ListingContractDate"], errors="coerce")
    date_issues = sold[sold["CloseDate"] < sold["ListingContractDate"]]
    print("\nDate Inconsistencies: ")
    print("CloseDate before ListingContractDate:", len(date_issues))

if "CountyOrParish" in sold.columns:
    county_prices = sold.groupby("CountyOrParish")["ClosePrice"].median()
    county_prices = county_prices.sort_values(ascending=False)
    print("\nCounties With Highest ClosePrice (Median):")
    print(county_prices.head())
    county_prices.to_csv(os.path.join(OUTPUT_DIRECTORY_FILES, "county_median_close_prices.csv"), index=True)


url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US"
mortgage = pd.read_csv(url, parse_dates=['observation_date'])
mortgage.columns = ['date', 'rate_30yr_fixed']

mortgage['year_month'] = mortgage['date'].dt.to_period('M')
mortgage_monthly = mortgage.groupby('year_month')['rate_30yr_fixed'].mean().reset_index()

sold['year_month'] = pd.to_datetime(sold['CloseDate']).dt.to_period('M')
sold_with_rates = sold.merge(mortgage_monthly, on='year_month', how='left')

listings_path = os.path.join(OUTPUT_DIRECTORY, 'listings.csv')
if os.path.exists(listings_path):
    listings = pd.read_csv(listings_path, low_memory=False)
    listings['year_month'] = pd.to_datetime(listings['ListingContractDate']).dt.to_period('M')
    listings_with_rates = listings.merge(mortgage_monthly, on='year_month', how='left')
    
    print("\nListings Unmatched Mortgage Rate Null Count:")
    print(listings_with_rates['rate_30yr_fixed'].isnull().sum())
    listings_with_rates.to_csv(os.path.join(OUTPUT_DIRECTORY, "CombinedListings_Enriched.csv"), index=False)

print("\nSold Unmatched Mortgage Rate Null Count:")
print(sold_with_rates['rate_30yr_fixed'].isnull().sum())

print("\nPreview Enriched Sold Data:")
print(sold_with_rates[['CloseDate', 'year_month', 'ClosePrice', 'rate_30yr_fixed']].head())

sold_with_rates.to_csv(os.path.join(OUTPUT_DIRECTORY, "CombinedSold_Validated.csv"), index=False)

