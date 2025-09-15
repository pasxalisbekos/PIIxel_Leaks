# Artifacts Overview

The provided artifacts represent both the collected datasets and the crawler implementation. The repository is split into two main components: our analysis tools examining Meta Pixel adoption across Tranco's top 1M websites and our hybrid crawler implementation that combines static analysis with headless browser detection to identify Meta Pixel instances. The primary dataset (`unified_pixel_dataset.json`) contains detailed information about Meta Pixel implementations, including configuration parameters, website rankings, categories, and tracked personally identifiable information (PII) across all analyzed domains. The analysis scripts are organized into specialized directories covering rank-based adoption patterns, parameter tracking analysis, domain categorization, and URL leakage investigation, while the crawler (`get_statically_all_pixel_instances.py`) provides the ability to replicate and extend this research.


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
pip install numpy pandas matplotlib seaborn tabulate requests aiohttp bs4
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

The remainder of this file details what scripts where used during the analysis with respect to the corresponding section in the document. Each plot is stored locally (with respect to the appropriate directory) as a PDF file.
## Table of Contents
- Section 3: Methodology
   - 3.1 Advanced Matching Configuration
- Section 4: Meta Pixel Adoption
  - 4.1 Hybrid vs Dynamic: Top 10K
  - 4.2 Meta Pixel Across 1M Websites
- Section 5: Customer Information Parameters
  - 5.1 Findings
- Section 6: Domain Categorization
  - 6.1 Meta Pixel Use across Different Categories
  - 6.2 Sensitive Categories
- Section 7: Meta Pixel In-Depth Browsing Tracking
  - 7.2 Depth of Tracking
- Appendix: Other Third Parties

## Section 3: Methodology

### 3.1 Advanced Matching Configuration

Our crawler is responsible for identifying Meta Pixel configuration files across the web. Its execution results into a dataset that stores all the information regarding of a Pixel implementation (default, GTM, etc) and the configuration file IDs found. All configuration file IDs are stored in : `./Results/Combined/per_domain_config_type.json`

In order to identify the PII configurations on a separate script we fetch the components of each configuration file following the URL: `https://connect.facebook.net/signals/config/{PIXEL_ID}`. We provide also the appropriate script that provides the PII configurations for each website located in: `./Analysis_Tranco1M/1_get_PII_from_configs.py`. This specific script gets the contents of the combined configuration IDs and proceeds on exploring them for PII leakage. We deployed this script across 4 EC2 instances each handling the configurations of 500K domains.

**Usage**:
```bash
python3 1_get_PII_from_configs.py start_index end_index
```

where start_/end_index are the indexes are the population of domains to be analyzed. For example one demo execution for the first 100 domains can be processed by running:
```bash
python3 1_get_PII_from_configs.py 0 100
```

- **NOTE:** For the current artifact/demo execution we provide an additional folder named `./temp_results` where you can locate the execution outcomes of PII identification. Each run results into a set of 3 files:
   - `per_domain_all_params_{start_index}_{end_index}.json` : Contains all the configuration IDs and the corresponding PII each configuration includes for a domain
   - `per_domain_total_params_{start_index}_{end_index}.json` : Contains all the PII that a website has configured (across all configurations) Pixel to collect
   - `valid_config_ids_{start_index}_{end_index}.json` : Contains the configuration IDs as well as their implementation method 


For our runs on tranco's 1M dataset, those findings/files can be located in the `./Validation_Results` directory, where there are 4 folders each corresponding to the outcomes of each ec2 instance.  


In addition to that we also provide 2 scripts:
- `2_combine_validation_results.py` : Combines the results (PII identifications) from all files into one (`./Results/Clean/valid_config_ids.json`) 
- `3_cleanup_after_validation.py` : Removes duplicates and stores all the configuration files resulting into PII leakage in the file  `./Results/Clean/fbp_config_ids_clean.json`. **This is the file the contains the PII and will be used to create the `unified_pixel_dataset.json` alongside with the files the comfort to the configuration type, website categories etc**



## Section 4: Meta Pixel Adoption

### 4.1 Hybrid vs Dynamic: Top 10K

**File**: `./Analysis_Top10K/cleanup_after_validation.py`

**Usage**:
```bash
python3 cleanup_after_validation.py
```

**Outputs**:
1. Meta Pixel implementations found per implementation method
2. Number of configuration files after validation and duplicate removal.
3. Differences per hybrid component with dynamic/headful crawling.
4. Description per case number for the 595 domains that were identified only during the headless crawls.

### 4.2 Meta Pixel Across 1M Websites

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

## Section 5: Customer Information Parameters

### 5.1 Findings

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



## Section 6: Domain Categorization

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
   
### 6.1 Meta Pixel Use across Different Categories
The following 2 plots display the configuration tendencies in the common web across the 10 most dominant categories utilizing Pixel. Figure 7 indicates Meta Pixel's configuration tendencies with respect to leaking vs not leaking a PII to Meta. Figure 8 displays the Meta Pixel configuration rate of each PII across those categories.
**Output File**: `per_category_leakage_tendencies.pdf`
   - Corresponds to Figure 7: Tracking configurations across Meta Pixel implementations in the top 10 website categories


**Output File**: `parameter_tracking_heatmap.pdf`
   - Corresponds to Figure 8: Parameter tracking rate by Pixel across top 10 website categories.
### 6.2 Sensitive Categories
The following 2 plots display similar structural characteristics with the aforementioned, but are adapted in the 8 sensitive categories from our dataset. Figure 9 displays the configuration tendencies whereas Figure 10 showcases the Meta Pixel configuration rate of each PII across sensitive websites.
**Output File**: `sensitive_categories_tracking_tendencies.pdf`
   - Corresponds to Figure 9: Tracking configurations across Meta Pixel implementations in **sensitive** website categories.

**Output File**: `sensitive_categories_parameter_tracking_heatmap.pdf`
   - Corresponds to Figure 10: Parameter tracking rate by Pixel across **sensitive** website categories.





## Section 7: Meta Pixel In-Depth Browsing Tracking

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



## APPENDIX B: OTHER THIRD PARTIES

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

In this repository the hybrid crawler's implementation is also provided under the Python script named: `get_statically_all_pixel_instances.py` that contains the implementation of both the static and headless components responsible for the identification of Facebook Pixel. To execute the file you can simply run:
```bash
python3 get_statically_all_pixel_instances.py -f test_domains.txt
```
We provide a sample list of some domains under the file `test_domains.txt`. The output of the crawler will be stored under the directory `crawler_output` which contains the following files:
1. pixels_found.json : Contains in a JSON format all the Facebook Pixel implementations that were found using only the static component of our crawler
2. state_fbq.json : Contains in a JSON format all the Facebook Pixel implementations that were found using only the headless component of the crawler
3. found_nothing.txt : Contains the list of domains where no Facebook Pixel instance was identified

And the error files:
1. flagged_erroneous_html_responses.json : Contains domains that identified our crawler as a both either blocked our access or re-directed it to a CAPTCHA challenge
2. invalid_html_no_response.txt : Contains domains that returned no response on our requests
3. total_hanged.txt : Contains domains which our visitation hanged (buffering)



# REPOSITORY STRUCTURE
- `./Analysis_Top10K` : Contains the artifacts regarding the Dynamic vs Static approaches
   - `./Consecutive_Runs`:
      - `./Dynamic`: 
         - `./verification`: Contains the files corresponding to a second run of the dynamic approach executed on the domains that where identified
         only using the dynamic approach. This was performed as a second step to verify that this identification was not caused by navigation or network errors. After this, we resulted in a set of 595 domains that the dynamic approach could not identify in general.
         - Contains the following files each corresponding to an instance ID that executed the crawl from the local environment (e.g. I1), where each instance handled a sub-set of domains from tranco's top 10K:
            - `{instance_id}_config_urls.json`: The Pixel configuration files captured in the traffic
            - `{instance_id}_erroneous_visits.json`: Domains that we could not browse due to Time Outs
            - `{instance_id}_navigation_errors.json`: Domains that we could not browse due other issues
            - `{instance_id}_report_urls.json`: The Pixel requests reporting the visitation on a domain that we visited
            - `{instance_id}_status_codes.json`: The status code of a domain visitation
            - `{instance_id}_timings.json`: The time for the analysis execution on each domain
         - **note:** The error and timing files where used for debugging during deployment

      - `./Static`:  Contains the execution results from the hybrid approach crawl
         -  `./only_dynamic`: This folder holds the findings regarding a run of the hybrid crawler 
         -  `./verifications`: This folder holds the findings regarding a verification run of the hybrid crawler (debugging purposes)
         -  `./with_increased_timeouts`: This folder holds the findings regarding the execution of the hybrid crawler where the dynamic component had an increased timeout value 
         -  All the above files and current directory contain similar to the following JSON and txt files used for the analysis
            - `baseline_timings.json`: Contains the total time required for a domain to be analyzed statically
            - `flagged_erroneous_html_responses.json`: Contains domain that returned an HTML indicating an error
            - `found_nothing.txt`: Contains the domains where browsing was complete successfully but no Pixel implementation was found
            - `headless_timings.json`: Contains the total time required for a domain to be analyzed dynamically (headless)
            - `invalid_html_no_response.txt`: Contains domains that returned an error in the WGET response
            - `pixels_found.json`: Contains the domains where a Pixel implementation was identified (STATICALLY)
            - `state_fbq.json`: Contains the domains where a Pixel implementation was identified (DYNAMIC-HEADLESS) 
            - `total_hanged.txt`: Contains domains that we never received a response to our WGET and eventually our navigation 'hanged'
   
   - `./Results` : Contains the results on the Pixel configurations of the hybrid crawler on the top 10K from the tranco list 
      - `./Clean`: Contains Pixel configurations with respect to PII after cleanup and validation
         -  `per_domain_all_params.json` : Contains all the configurations and their corresponding PII for each domain
         -  `per_domain_total_params.json` : Contains all PII that are configured through Pixel for each domain (across all configurations on that domain)
         -  `valid_config_ids.json`: Contains the validated configuration IDs 
   
      - `./Combined`: Contains the different types of Pixel implementations (e.g. default, GMT, vpt, other third parties etc)
         -  `per_case_pixels.json`: Contains the configurations as a dictionary with key each configuration type
         -  `per_domain_config_type.json`: Contains the configuration types as a dictionary with keys the domains
   
   
   - `cleanup_after_validation.py`: The script responsible for removing duplicates and invalid config IDs from the dataset after the validation process
   - `extra_found_on_hybrid` : Contains the extra domains that the hybrid apporach identified utilizing Pixel
   - `per_case_pixels.json` : Contains the Pixel implementation method for the extra domains
   - `solely_static.csv` : Contains notes regarding the manual investigation on the extra domains that the hybrid approach identified utilizing Pixel

- `./Analysis_Tranco1M`: Contains the artifacts regarding tranco's 1M websites
   - `./Categories`: Contains the folders corresponding to the categorization crawling results executed on each EC2 instance following the conversion of `./e{ID}`. Each file contains a folder named `./Categories` where the results are stored under the following files:
      -  `per_categories_doms_{start_index}_{end_index}.json`: This file contains the categorization results with keys the categories and values the domains corresponding to that category
      -  `per_domain_categories_{start_index}_{end_index}.json`: This file contains the categorization results with keys the domains and values the catories under which this domain falls

   - `./Categories_Analysis`: Contains the script necessary for the **Categorization Analysis** (the contents have beed discussed in the sections above)
   - `./Full_URL_Leakage`: Contains the script necessary for the **URL leakage Analysis** (the contents have beed discussed in the sections above)
   - `./Other_TP`: Contains the script necessary for the **Other Third Party Analysis** (the contents have beed discussed in the sections above)
   - `./Parameters_Analysis`: Contains the script necessary for the **Parameter Analysis** (the contents have beed discussed in the sections above)
   - `./Rank_Analysis`: Contains the script necessary for the **Rank Analysis** (the contents have beed discussed in the sections above)
   
   - `./Results`: Contains the results on the Pixel configurations of the hybrid crawler on the Trano's 1M from the tranco list 
      - `./Clean`: Contains Pixel configurations with respect to PII after cleanup and validation
         -  `per_domain_all_params.json` : Contains all the configurations and their corresponding PII for each domain
         -  `per_domain_total_params.json` : Contains all PII that are configured through Pixel for each domain (across all configurations on that domain)
         -  `valid_config_ids.json`: Contains the validated configuration IDs 

   - `./RESULTS_EC2`: Contains folder corresponding the the hybrid crawling executed on each EC2 instance. The folder holding the results of an ec2 instance is named `./e{ID}` and the results are stored in the `./Static` sub-folder. Each execution is characterized by `{start_index}_{end_index}_{population_start}_{population_end}` where: start and end index described the total range of domains and population corresponds to the sub-population from that range that was crawled from this instance e.g.  100K_200K_20_30K --> Domains 120K-130K. All those directories hold the following folders:
      - `baseline_timings.json`: Contains the total time required for a domain to be analyzed statically
      - `flagged_erroneous_html_responses.json`: Contains domain that returned an HTML indicating an error
      - `found_nothing.txt`: Contains the domains where browsing was complete successfully but no Pixel implementation was found
      - `headless_timings.json`: Contains the total time required for a domain to be analyzed dynamically (headless)
      - `invalid_html_no_response.txt`: Contains domains that returned an error in the WGET response
      - `pixels_found.json`: Contains the domains where a Pixel implementation was identified (STATICALLY)
      - `state_fbq.json`: Contains the domains where a Pixel implementation was identified (DYNAMIC-HEADLESS) 
      - `total_hanged.txt`: Contains domains that we never received a response to our WGET and eventually our navigation 'hanged'

   
   - `./temp_results`: 
      - This folder is only for demo purposes where an execution of the Pixel configuration crawler stores its results
   
   - `./Validation_Results`: Contains the results of each EC2 instance with respect to configuration file crawling (e.g. instance e2). All the sub-directories hold the following files:
      - `per_domain_all_params_{start_index}_{end_index}.json` : Contains all the configuration IDs and the corresponding PII each configuration includes for a domain
      - `per_domain_total_params_{start_index}_{end_index}.json` : Contains all the PII that a website has configured (across all configurations) Pixel to collect
      - `valid_config_ids_{start_index}_{end_index}.json` : Contains the configuration IDs as well as their implementation method 


   -  `1_get_PII_from_configs.py`: This is the code responsible for fetching an analyzing a configuration file based on the Pixel ID
   -  `2_combined_validation_results.py`: Combine all PII configurations into 1 file
   -  `3_cleanup_after_validation.py`: Remove duplicates and merge the PII dataset into a single clean file 
   -  `create_unified_dataset.py`: Uses all appropriate files to gather and merge the PII, configuration type and categories across all domains
   -  `unified_pixel_dataset.json`: Contains all Pixel implementation, the configured PII and categories across all domains

- `crawler_output` : Contains files corresponding to a demo run of the hybrid crawler
- `tranco` : Contains the domains from the tranco list
- `get_statically_all_pixel_instances.py`:  The hybrid crawler implementation
- `test_domains.txt` : A file containing domains for a demo run of the crawler

