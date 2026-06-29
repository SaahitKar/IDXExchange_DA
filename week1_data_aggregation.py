import pandas as pd 
import glob
import os

#File Locations
DATA_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Data Files')
OUTPUT_DIRECTORY = os.path.join(os.path.dirname(__file__), '..', 'Output Files')
os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)

#Find all Listing Files in Data
files_listings = glob.glob(os.path.join(DATA_DIRECTORY, 'CRMLSListing*.csv'))
print(f"Found {len(files_listings)} listing files")

#Find all Sold Files in Data
files_sold = glob.glob(os.path.join(DATA_DIRECTORY, 'CRMLSSold*.csv'))
print(f"Found {len(files_sold)} sold files")

#Store Files Into Listings Array 
listing_frames = []
for f in sorted(files_listings):
    df = pd.read_csv(f)
    listing_frames.append(df)

#Store Files Into Listings Array 
sold_frames = []
for f in sorted(files_sold):
    df = pd.read_csv(f)
    sold_frames.append(df)

#Combine all Listings Files into One DataFrame
combined_listings = pd.concat(listing_frames, ignore_index=True)
print(f"Rows after concatenation: {len(combined_listings)}")

#Combine all Sold Files into One DataFrame
combined_sold = pd.concat(sold_frames, ignore_index=True)
print(f"Rows after concatenation: {len(combined_sold)}")

#Filter for Residential Property Listings
before_listings = len(combined_listings)
combined = combined_listings[combined_listings['PropertyType'] == 'Residential']
after_listings = len(combined_listings)

#Filter for Sold Property Listings
before_sold = len(combined_sold)
combined = combined_sold[combined_sold['PropertyType'] == 'Residential']
after_sold = len(combined_sold)

#Check To See if Filter Worked for Listings
print("Listings:")
print(f"Rows Before Residential Filter Applied: {before_listings}")
print(f"Rows After Residential Filter Applied: {after_listings}")

#Check To See if Filter Worked for Sold
print("Sold:")
print(f"Rows Before Residential Filter Applied: {before_sold}")
print(f"Rows After Residential Filter Applied: {after_sold}")

#Output Combined Listing Data to CSV
output_path = os.path.join(OUTPUT_DIRECTORY, 'listings.csv')
combined.to_csv(output_path, index=False)
print(f"Saved to {output_path}")

#Output Combined Sold Data to CSV
output_path = os.path.join(OUTPUT_DIRECTORY, 'sold.csv')
combined.to_csv(output_path, index=False)
print(f"Saved to {output_path}")
