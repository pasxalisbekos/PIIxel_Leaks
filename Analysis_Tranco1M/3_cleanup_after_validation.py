import os
import re
import json
import sys
from urllib.parse import urlparse
import requests


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


# static_only, headless_only = get_domains_static_found()

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
    
    print('==========================================================')
    print(f"Total domains: {len(cleaned_domains)} after validation only and duplicate removal")
    # print(f"Domains with pixels after deduplication: {non_empty_domains}")
    print(f"Pixels removed (appearing in > {threshold} domains with value 'GTM_BASECODE_PIXEL.potential'): {len(removed_pixels)}")
    print('==========================================================')
    if removed_pixels:
        print('Top 10 Removed Pixel IDs:')
        for i, (pixel_id, domains) in enumerate(sorted(removed_pixels.items(), 
                                                      key=lambda x: len(x[1]), 
                                                      reverse=True)[:10]):
            print(f"  Pixel ID {pixel_id} removed from {len(domains)} domains:")
            print(f"    Example domains: {', '.join(domains[:5])}...")
            if i >= 9:
                remaining = len(removed_pixels) - 10
                if remaining > 0:
                    print(f"  ... and {remaining} more pixel IDs")
                break
    print('==========================================================')
    
    # with open('./temp.json', 'w') as f:
    #     json.dump(cleaned_domains, f, indent=4)
    print(len(cleaned_domains))
    return cleaned_domains


if __name__ == "__main__":

    valid_configs = get_valid_configs_static()

    print(len(valid_configs))
    # for domain in valid_configs.keys():
    #     if len(valid_configs[domain]) == 0:
    #         print(valid_configs[domain])
    #         exit()
    # exit()
    clean_doms = remove_duplicate_pixel_ids(valid_configs)
    
    count = 0
    for domain in clean_doms.keys():
        if len(clean_doms[domain]) == 0:
            count+=1

    print(f'Invalid configs (empty set for domain) {count}')
    clean_doms = {domain: value for domain, value in clean_doms.items() if value}

    domains_to_remove = []
    for domain in clean_doms.keys():
        items = clean_doms[domain]

        potential_count = 0
        for key in items.keys():
            if items[key] == 'GTM_LIGHTWEIGHT_PIXEL.potential' or items[key] == 'GTM_BASECODE_PIXEL.potential':
                potential_count += 1
        
        if potential_count > 5:
            domains_to_remove.append(domain)

    filtered_clean = {k: v for k, v in clean_doms.items() if k not in domains_to_remove}


    print(f'After threshold removal for `potential Pixel IDs` ({len(domains_to_remove)}) Total Domains Operating Pixel: {len(filtered_clean)}')
    # exit()
    # with open('./Results/Clean/fbp_config_ids_clean.json','w') as f:
    #     json.dump(filtered_clean, f, indent=4)
    # f.close()
    