import os
import pandas as pd
import matplotlib.pyplot as plt

#Load Week 1 Sold Data

# DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Data Files')
# OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Output Files')
# os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

# output_path = os.path.join(OUTPUT_DIRECTORY, 'sold.csv')
sold = pd.read_csv("sold.csv", low_memory=False)

#Inspect Datatset Structure
print("Rows & Columns: ", sold.shape)

#Print Number of Unique Property Types
print("\nNumber of Unique Property Types: ", sold["PropertyType"].nunique())

print("\nProperty Types:")
print(sold["PropertyType"].value_counts(dropna=False))

#Filter for Only Residential Property Types
print("\nRows before Residential filter:", len(sold))
sold = sold[sold["PropertyType"] == "Residential"]
print("Rows after Residential filter:", len(sold))

#Check for Missing Values
missing = pd.DataFrame({
    "Missing Count": sold.isnull().sum(),
    "Missing Percent": sold.isnull().mean() * 100
})

missing = missing.sort_values(
    by="Missing Percent",
    ascending=False
)

print("\nMissing value report:")
print(missing)

# Flag columns with more than 90% missing values
high_missing = missing[
    missing["Missing Percent"] > 90
]

print("\nColumns with more than 90% missing values:")
print(high_missing)

#Save Missing Value Reports
missing.to_csv("missing_value_report.csv")
high_missing.to_csv("high_missing_columns_over_90.csv")

