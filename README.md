# Artifacts Overview

The provided artifacts represent both the collected datasets and the crawler implementation. The repository is split into two main components: our analysis tools examining Meta Pixel adoption across Tranco's top 1M websites and our hybrid crawler implementation that combines static analysis with headless browser detection to identify Meta Pixel instances. The primary dataset (`unified_pixel_dataset.json`) contains detailed information about Meta Pixel implementations, including configuration parameters, website rankings, categories, and tracked personally identifiable information (PII) across all analyzed domains. The analysis scripts are organized into specialized directories covering rank-based adoption patterns, parameter tracking analysis, domain categorization, and URL leakage investigation, while the crawler (`PII_Hybrid_Crawler.py`) provides the ability to replicate and extend this research.


# Requirements
For the crawler's execution make sure you system has Python3 installed and the appropriate Selenium and Chrome packages:
```bash
sudo apt update
sudo apt install -y python3 python3-pip wget
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable
pip install selenium webdriver-manager
```

Our analysis was executed in an Ubuntu based machine operating Ubuntu 22.04.5 LTS and Python's version **3.11.10**. The additional Python packages required can be installed as described below:

```bash
pip install numpy pandas matplotlib seaborn tabulate requests 
```
All plots are saved locally in the corresponding directory.


# Meta Pixel Analysis Tools

This repository also contains the artifacts for the analysis performed with respect to Meta Pixel adoption across Tranco's 1M websites and their corresponding configuration files. The overall dataset of Meta Pixel implementations we identified is located in the file `unified_pixel_dataset.json`. This file contains for every website:
1. The Meta Pixel IDs corresponding to a configuration file
2. The type of Meta Pixel implementation
3. The rank of the website
4. The categories under which this website comforts to
5. The parameters (PII) that are configured to be tracked across all configurations of Meta Pixel in this website

The overall dataset containing information about each web-site's Meta Pixel implementation, parameters been tracked, categories and rank can be located in the file:

**File**: `./Analysis_Tranco1M/unified_pixel_dataset.json`

The remainder of this file details what scripts where used during the analysis with each plot stored locally (with respect to the appropriate directory) as a PDF file.
## Table of Contents
- Meta Pixel Adoption
  - Hybrid vs Dynamic: Top 10K
  - Meta Pixel Across 1M Websites
- Customer Information Parameters
  - Findings
- Domain Categorization
  - Meta Pixel Use across Different Categories
  - Sensitive Categories
- Meta Pixel In-Depth Browsing Tracking
  - Depth of Tracking
- Other Third Parties

## Meta Pixel Adoption

### Hybrid vs Dynamic: Top 10K

**File**: `./Analysis_Top10/cleanup_after_validation.py`

**Usage**:
```bash
python3 cleanup_after_validation.py
```

**Outputs**:
1. Meta Pixel implementations found per implementation method
2. Number of configuration files after validation and duplicate removal.
3. Differences per hybrid component with dynamic/headful crawling.
4. Description per case number for the 595 domains that were identified only during the headless crawls.

### Meta Pixel Across 1M Websites

#### Meta Pixel Implementation Validation

**File**: `./Analysis_Tranco1M/cleanup_after_validation.py`

**Usage**:
```bash
python3 cleanup_after_validation.py
```

**Outputs**:
1. The number of Meta Pixel implementations after validation of configurations and duplicate removal.

#### Rank Analysis

**File**: `./Analysis_Tranco1M/Rank_Analysis/per_rank_adoption.py`

**Usage**:
```bash
python3 per_rank_adoption.py
```

**Outputs**:
1. Table 1: Distribution of Meta Pixel instance types.
2. Figure 4: Per ranking bin Meta Pixel adoption rates.
   - Saved locally as: `facebook_pixel_adoption_by_rank.pdf`

## Customer Information Parameters

### Findings

**File**: `./Analysis_Tranco1M/Parameters_Analysis/per_rank_parameters.py`

**Usage**:
```bash
python3 per_rank_parameters.py
```

**Outputs**:
1. Number of total websites tracking at least one parameter through Meta Pixel.
2. Figure 5: Parameter tracking rates across rank bins of 100K.
   - Saved locally as: `parameter_adoption_per_rank.pdf`


**File**: `./Analysis_Tranco1M/Parameters_Analysis/param_combination.py`

**Usage**:
```bash
python3 param_combination.py
```

**Outputs**:
1. Top 10 most widely used combinations count with the corresponding PII on each combination (including also ``None'' as the combination that has configured no parameters to be tracked).
2. Figure 6: Top-5 most commonly tracked combinations of Meta Pixel parameters.
   - Saved locally as `parameter_combo_distribution.pdf`



## Domain Categorization

**File**: `Analysis_Tranco1M/Categories_Analysis/categorization_analysis.py`

**Usage**:
```bash
python3 categorization_analysis.py
```

**Outputs**:
1. For each Category (order based on the population size):
   a. The total population of websites utilizing Meta Pixel.
   b. The number of websites configuring at least one parameter to be tracked through Meta's Pixel.
   c. The number of websites with no parameters in their Meta Pixel's configuration file.
2. The number of sensitive websites in total based on our categorization process.
3. Four different plots (saved locally) as described bellow:
   
### Meta Pixel Use across Different Categories
The following 2 plots display the configuration tendencies in the common web across the 10 most dominant categories utilizing Pixel. Figure 7 indicates Meta Pixel's configuration tendencies with respect to leaking vs not leaking a PII to Meta. Figure 8 displays the Meta Pixel configuration rate of each PII across those categories.
**Output File**: `per_category_leakage_tendencies.pdf`
   - Corresponds to Figure 7: Tracking configurations across Meta Pixel implementations in the top 10 website categories


**Output File**: `parameter_tracking_heatmap.pdf`
   - Corresponds to Figure 8: Parameter tracking rate by Pixel across top 10 website categories.
### Sensitive Categories
The following 2 plots display similar structural characteristics with the aforementioned, but are adapted in the 8 sensitive categories from our dataset. Figure 9 displays the configuration tendencies whereas Figure 10 showcases the Meta Pixel configuration rate of each PII across sensitive websites.
**Output File**: `sensitive_categories_tracking_tendencies.pdf`
   - Corresponds to Figure 9: Tracking configurations across Meta Pixel implementations in **sensitive** website categories.

**Output File**: `sensitive_categories_parameter_tracking_heatmap.pdf`
   - Corresponds to Figure 10: Parameter tracking rate by Pixel across **sensitive** website categories.





## Meta Pixel In-Depth Browsing Tracking

**File**: `Analysis_Tranco1M/Full_URL_Leakage/check_captured_lens.py`

**Usage**:
```bash
python3 check_captured_lens.py
```

**Outputs**:

1. For each category:
   a. The description and population of each entry in the navigation logs collected with respect to URL leakage through Meta Pixel towards Meta.
   b. The total number of navigation logs of websites leaking the full browsing journey of a user through Meta's Pixel towards Meta.
   c. The total number of those websites that also leak at least one PII through Meta's Pixel.

2. Figure 11: Parameter tracking rate by Pixel across websites leaking the navigation history of the user.
   - Saved locally as `URL_leakage_with_PII_leakage.pdf`



## OTHER THIRD PARTIES

**File**: `Analysis_Tranco1M/Other_TP/other_third_parties.py`

**Usage**:
```bash
python3 other_third_parties.py
```

**Outputs**:

1. The total number of websites that configure Pixel through either a custom or a third-party script (excluding GTM)

2. Figure 12:  Domain distribution of scripts used to load Meta Pixel.
   - Saved locally as `distribution_plot.pdf`






# Crawler Implementation

In this repository the hybrid crawler's implementation is also provided under the Python script named: `PII_Hybrid_Crawler.py` that contains the implementation of both the static and headless components responsible for the identification of Facebook Pixel. To execute the file you can simply run:
```bash
python3 PII_Hybrid_Crawler.py -f test_domains.txt
```
We provide a sample list of some domains under the file `test_domains.txt`. The output of the crawler will be stored under the directory `crawler_output` which contains the following files:
1. pixels_found.json : Contains in a JSON format all the Facebook Pixel implementations that were found using only the static component of our crawler
2. state_fbq.json : Contains in a JSON format all the Facebook Pixel implementations that were found using only the headless component of the crawler
3. found_nothing.txt : Contains the list of domains where no Facebook Pixel instance was identified

And the error files:
1. flagged_erroneous_html_responses.json : Contains domains that identified our crawler as a both either blocked our access or re-directed it to a CAPTCHA challenge
2. invalid_html_no_response.txt : Contains domains that returned no response on our requests
3. total_hanged.txt : Contains domains which our visitation hanged (buffering)
