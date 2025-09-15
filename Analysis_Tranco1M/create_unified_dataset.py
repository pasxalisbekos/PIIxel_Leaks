import os
import re
import json
import sys
import pandas as pd


fbpixel_websites = {}
with open('./Results/Clean/fbp_config_ids_clean.json','r') as f:
    fbpixel_websites = json.load(f)
    f.close()


categories_directory = './Categories'
def get_categories_dicts(directory_path):

    per_domain_categories = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.startswith("per_domain_categories"):
                temp_path = os.path.join(path,name)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in per_domain_categories.keys():
                            if domain in fbpixel_websites.keys():
                                per_domain_categories[domain] = temp_domains[domain]

    return per_domain_categories

def get_params_found(directory_path):
    params_dict = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.startswith("per_domain_total_params_"):
                temp_path = os.path.join(path,name)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in params_dict.keys():
                            if domain in fbpixel_websites.keys():
                                params_dict[domain] = temp_domains[domain]

    return params_dict


def read_tranco_list(file_path):
    domains_dict = {}
    
    try:
        df = pd.read_csv(file_path, header=None, names=['rank', 'domain'])
        domains_dict = dict(zip(df['domain'], df['rank']))
        
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"Error reading file: {e}")
    
    return domains_dict



tranco_path = '../tranco/top-1m.csv'
per_domain_categories = get_categories_dicts(categories_directory)
params_dict = get_params_found('./Validation_Results/')
tranco_domains = read_tranco_list(tranco_path)


print(f'Total websites utilizing Pixels (validated): {len(fbpixel_websites)}')
print(f'Total websites with a categorization result (cleaned): {len(per_domain_categories)}')



per_domain_overall_findings = dict()


for domain in fbpixel_websites.keys():

    pixels_n_types = fbpixel_websites[domain]
    pixels = list(set(pixels_n_types.keys()))
    types = list(set(pixels_n_types.values()))
    rank = tranco_domains[domain]
    categories = per_domain_categories[domain]
    parameters = []
    if domain in params_dict.keys():
        parameters = params_dict[domain]

    item = {
        'Pixel_IDs' : pixels,
        'Pixel_Types' : types,
        'Rank' : rank,
        'Categories' : categories,
        'Parameters' : parameters
    }

    if domain not in per_domain_overall_findings.keys():
        per_domain_overall_findings[domain] = item


with open('./unified_pixel_dataset.json','w') as f:
    json.dump(per_domain_overall_findings, f, indent=4)
    f.close()


# print(len(per_domain_overall_findings))