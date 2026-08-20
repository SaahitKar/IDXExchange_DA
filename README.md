# IDX-Exchange Internship Work


## Week 0 – MLS Data Pipeline

### Completed:

* Downloaded available CRMLS listing and sold files from January 2024 through May 2026.
* Reviewed the Trestle Property Metadata document to understand field definitions, data types, and available property attributes.

## Week 1 – Monthly Dataset Aggregation

### Completed:

* Concatenated monthly files into two combined datasets and saved as:
  * `sold_unfiltered.csv`
  * `listings_unfiltered.csv`
* Filtered both datasets to `PropertyType == "Residential"` and saved as:
  * `sold.csv`
  * `listings.csv`

### Key Results

Sold dataset row count:

* After concatenation: 639,877
* After Residential filter: 430,438

Listings dataset row count:

* After concatenation: 925,111
* After Residential filter: 588,671
