import os
import re
import json
import sys
from urllib.parse import urlparse
import requests
import pandas as pd

def get_domains_static_found(directory_path):
    static_only = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.endswith("pixels_found.json"):
                temp_path = os.path.join(path,name)
                print(temp_path)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in static_only.keys():
                            static_only[domain] = temp_domains[domain]

    headless_only = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.endswith("state_fbq.json"):
                temp_path = os.path.join(path,name)
                print(temp_path)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in headless_only.keys():
                            headless_only[domain] = temp_domains[domain]
    


    return static_only, headless_only

def get_domains_dynamic_found(dynamic_folder):
    fbp_domains = []
    for path, subdirs, files in os.walk(dynamic_folder):
        for name in files:
            if name.endswith("_config_urls.json"):
                temp_path = os.path.join(path,name)
                print(temp_path)
                temp = []
                with open(temp_path,"r") as f:
                    temp = json.load(f)
                    for key in temp.keys():
                        fbp_domains.append(key.replace('www.',''))

    for path, subdirs, files in os.walk(dynamic_folder):
        for name in files:
            if name.endswith("_report_urls.json"):
                temp_path = os.path.join(path,name)
                temp = []
                with open(temp_path,"r") as f:
                    temp = json.load(f)
                    for key in temp.keys():
                        if key.replace('www.','') not in fbp_domains:
                            fbp_domains.append(key.replace('www.',''))

    fbp_domains = list(set(fbp_domains))
    return fbp_domains



def get_valid_configs_static():
    valid_configs = {}
    with open('./Results/Clean/valid_config_ids.json', 'r') as f:
        temp = json.load(f)
        for domain in temp:
            if len(temp[domain]) > 0:
                valid_configs[domain] = temp[domain]
        f.close()

    return valid_configs





def remove_duplicate_pixel_ids(valid_domains_total, threshold=3):
    pixel_counts = {}  
    pixel_domains = {} 

    for domain, pixels in valid_domains_total.items():
        for pixel_id, pixel_value in pixels.items():
            if pixel_id not in pixel_counts:
                pixel_counts[pixel_id] = 0
                pixel_domains[pixel_id] = []
            pixel_counts[pixel_id] += 1
            pixel_domains[pixel_id].append((domain, pixel_value))
    
    removed_pixels = {}  
    cleaned_domains = {}
    
    for domain, pixels in valid_domains_total.items():
        cleaned_domains[domain] = {}
        
        for pixel_id, pixel_value in pixels.items():
            should_remove = (
                pixel_counts[pixel_id] > threshold and
                pixel_value == "GTM_BASECODE_PIXEL.potential"
            )
            
            if not should_remove:
                cleaned_domains[domain][pixel_id] = pixel_value
            else:
                if pixel_id not in removed_pixels:
                    removed_pixels[pixel_id] = []
                removed_pixels[pixel_id].append(domain)
    
    non_empty_domains = sum(1 for domain in cleaned_domains if cleaned_domains[domain])
    
    return cleaned_domains


def count_domains_by_description(csv_path):
    df = pd.read_csv(csv_path)
    description_counts = {}
    
    for description, group in df.groupby('EXPLANATION'):
        unique_domains = group['DOMAIN'].nunique()
        description_counts[description] = unique_domains
    
    return description_counts

if __name__ == "__main__":

    valid_configs = get_valid_configs_static()
    clean_doms = remove_duplicate_pixel_ids(valid_configs)
    clean_doms = {domain: value for domain, value in clean_doms.items() if value}



    static_only, headless_only = get_domains_static_found('./Consecutive_Runs/Static')
    dynamic_only = get_domains_dynamic_found('./Consecutive_Runs/Dynamic')



    print("\nDomain Counts:")
    print(f"\t Static-Only Domains: {len(static_only)}")
    print(f"\t Headless-Only Domains: {len(headless_only)}")
    print(f"\t Dynamic-Only Domains: {len(dynamic_only)}\n")
    print('============================================================================================================================================================\n')
    print(f"\t Valid Configurations: {len(clean_doms)}\n")
    print('============================================================================================================================================================\n')
    not_found_in_static_only = []
    only_with_static = []
    for domain in dynamic_only:
        if domain not in static_only:
            not_found_in_static_only.append(domain)
        else:
            only_with_static.append(domain)

    print('============================================================================================================================================================\n')
    print(f'\t Total domains found in dynamic BUT NOT static: {len(not_found_in_static_only)}')
    print(f'\t Total domains found in dynamic AND static: {len(only_with_static)}\n')
    print('============================================================================================================================================================\n')
    not_headless_and_static = []
    only_headless = []
    for domain in not_found_in_static_only:
        if domain not in headless_only:
            not_headless_and_static.append(domain)
        else:
            only_headless.append(domain)

    print('============================================================================================================================================================\n')
    print(f'\t Total domains found in dynamic BUT NOT static & headless: {len(not_headless_and_static)}')
    print(f'\t Total domains found in dynamic AND headless: {len(only_headless)}\n')
    print('============================================================================================================================================================\n')


    state_but_not_dynamic = dict()
    unique_state_types = dict()
    for domain in headless_only.keys():
        if domain not in dynamic_only:
            if domain in clean_doms.keys():
                state_type = headless_only[domain]['state_type']            
                state_but_not_dynamic[domain] = state_type
                if state_type not in unique_state_types.keys():
                    unique_state_types[state_type] = 1
                else:
                    unique_state_types[state_type] += 1


    static_but_not_dynamic = dict()
    unique_static_types = dict()
    for domain in static_only.keys():
        if domain not in dynamic_only:
            if domain in clean_doms.keys() and domain not in headless_only.keys():
                static_but_not_dynamic[domain] = list()
                types = list(static_only[domain].keys())
                for type_ in types:
                    static_but_not_dynamic[domain].append(type_)
                    if type_ not in unique_static_types.keys():
                        unique_static_types[type_] = 1
                    else:
                        unique_static_types[type_] += 1

    extra_on_hybrid = []
    for domain in headless_only.keys():
        if domain not in dynamic_only:
            if domain in clean_doms.keys():
                extra_on_hybrid.append(domain)

    
    for domain in static_only.keys():
        if domain not in dynamic_only:
            if domain in clean_doms.keys():
                if domain not in extra_on_hybrid:
                    extra_on_hybrid.append(domain)

    print('============================================================================================================================================================\n')
    print(f'\t Found in headless but not in dynamic : {len(state_but_not_dynamic.keys())} | State types: {unique_state_types}')
    print(f'\t Found in static but not in dynamic   : {len(static_but_not_dynamic.keys())} | State types: {unique_static_types}\n')
    print('============================================================================================================================================================\n')


    
result = count_domains_by_description('./solely_static.csv')
print("Description Counts of solely statically identified Pixels:")
result = dict(sorted(result.items(), key=lambda item: item[1], reverse=True))
for description, count in result.items():
    print(f"'{description}': {count} ({round((count*100)/595,2)})")





