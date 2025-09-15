import os
import re
import json
import sys
from urllib.parse import urlparse
import requests


start_index = 0
end_index = 0

config_pattern = r'config\.set\("(\d+)", "automaticMatching", ({.*?})\)'
per_user_param = {
    "em": 0,
    "ph": 0,
    "ge": 0,
    "db": 0,
    "ct": 0,
    "st": 0,
    "zp": 0,
    "country": 0,
    "fn": 0,
    "ln": 0,
    "external_id": 0
}


per_user_param_websites = {
    "em": [],
    "ph": [],
    "ge": [],
    "db": [],
    "ct": [],
    "st": [],
    "zp": [],
    "country": [],
    "fn": [],
    "ln": [],
    "external_id": []
}
per_domain_configs = {}
with open('./Results/Combined/per_domain_config_type.json', 'r') as f:
    per_domain_configs = json.load(f)
    f.close()


def extract_hostname(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def check_fb_pixel(unique_id,domain):
    base_url = f'https://connect.facebook.net/signals/config/{unique_id}?domain={domain}'
    
    try:
        response = requests.get(base_url, timeout=3, allow_redirects=True)
        
        if response.status_code != 200:
            print(f'Invalid status code for {unique_id}')
            return 0, []
        
        pattern = rf'fbq\.registerPlugin\("{unique_id}", \{{__fbEventsPlugin: 1, plugin: function\(fbq, instance, config\) \{{ /\* empty plugin \*/instance\.configLoaded\("{unique_id}"\); \}}\}}\);?\s*$'
        
        if re.search(pattern, response.text.strip()):
            print(f"Invalid ID: {unique_id} ({domain})")
            return 0, []
        else:
            found = re.findall(config_pattern, response.text)
            if found:
                for match in found:
                    if match[1]:
                        parameters = match[1].split('[')[1].replace(']}','').replace('"','').split(",")
                        return 1, parameters
            else:
                return 1, []
            
            return 0,[]
            
    except requests.exceptions.RequestException as e:
        print(f"Error checking {unique_id}: {str(e)}")
        return 0, []



def validate_config_ids(start_index,end_index):
    per_domain_valid_configs = dict()
    per_domain_all_pixel_params = dict()
    per_domain_total_params = dict()

    counter = 0
    configs_to_explore = list(per_domain_configs.keys())
    configs_to_explore = configs_to_explore[start_index:end_index]


    for domain in configs_to_explore:
        print('=========================================================================================')
        print(f'Validating configs for {domain} ({counter}/{len(configs_to_explore)})')
        valid_config_ids = dict()
        for config_id in per_domain_configs[domain].keys():
            print(f'Checking config {config_id}')
            is_valid,parameters = check_fb_pixel(config_id,domain)
            if is_valid == 0:
                print(f'Invalid {config_id} for domain: {domain}')
            else:
                valid_config_ids[config_id] = per_domain_configs[domain][config_id]
                if len(parameters) > 0:
                    if domain not in per_domain_all_pixel_params.keys():
                        per_domain_all_pixel_params[domain] = dict()

                    if config_id not in per_domain_all_pixel_params[domain].keys():              
                        per_domain_all_pixel_params[domain][config_id] = parameters


                    if domain not in per_domain_total_params.keys():
                        per_domain_total_params[domain] = list()

                    for param in parameters:
                        if param not in per_domain_total_params[domain]:
                            per_domain_total_params[domain].append(param)

                    print(f'{config_id}  ---> {str(parameters)}')
        counter += 1
        print('=========================================================================================')


        per_domain_valid_configs[domain] = valid_config_ids

    counter = 0
    print('Second round of validation: ....')
    domains_inval = []
    for domain in configs_to_explore:
        if domain not in per_domain_valid_configs.keys():
            domains_inval.append(domain)
        else:
            if len(per_domain_configs[domain]) == 0:
                domains_inval.append(domain)

    for domain in domains_inval:
        print('=========================================================================================')
        print(f'Validating configs for {domain} ({counter}/{len(domains_inval)})')
        valid_config_ids = dict()
        for config_id in per_domain_configs[domain].keys():
            print(f'Checking config {config_id}')
            is_valid,parameters = check_fb_pixel(config_id,domain)
            if is_valid == 0:
                print(f'Invalid {config_id} for domain: {domain}')
            else:
                valid_config_ids[config_id] = per_domain_configs[domain][config_id]
                if len(parameters) > 0:
                    if domain not in per_domain_all_pixel_params.keys():
                        per_domain_all_pixel_params[domain] = dict()

                    if config_id not in per_domain_all_pixel_params[domain].keys():              
                        per_domain_all_pixel_params[domain][config_id] = parameters


                    if domain not in per_domain_total_params.keys():
                        per_domain_total_params[domain] = list()

                    for param in parameters:
                        if param not in per_domain_total_params[domain]:
                            per_domain_total_params[domain].append(param)

                    print(f'{config_id}  ---> {str(parameters)}')

        print('=========================================================================================')
        counter += 1


    with open(f'./temp_results/valid_config_ids_{start_index}_{end_index}.json', 'w') as f:
        json.dump(per_domain_valid_configs, f, indent=4)
        f.close()

    with open(f'./temp_results/per_domain_all_params_{start_index}_{end_index}.json', 'w') as f: # per config params for every config belonging to a domain
        json.dump(per_domain_all_pixel_params, f, indent=4)
        f.close()

    with open(f'./temp_results/per_domain_total_params_{start_index}_{end_index}.json', 'w') as f: # all params as unique set been tracked in this domain regardless of Pixel ID
        json.dump(per_domain_total_params, f, indent=4)
        f.close()
        
    return per_domain_valid_configs



def validate_arguments():
    if len(sys.argv) != 3:
        print("Error: Invalid number of arguments")
        print("Usage: python3 verify_pixels_and_remove_duplicates.py start_index end_index")
        print("Example: python3 verify_pixels_and_remove_duplicates.py 1 1000")
        sys.exit(1)
    
    try:
        start_index = int(sys.argv[1])
        end_index = int(sys.argv[2])
    except ValueError:
        print("Error: Both start_index and end_index must be integers")
        print("Usage: python3 verify_pixels_and_remove_duplicates.py start_index end_index")
        print("Example: python3 verify_pixels_and_remove_duplicates.py 1 1000")
        sys.exit(1)
    
    if start_index > end_index:
        print("Error: start_index must be less than or equal to end_index")
        print(f"You provided: start_index={start_index}, end_index={end_index}")
        sys.exit(1)
    
    if start_index < 0 or end_index < 0:
        print("Error: Both indices must be positive integers")
        print(f"You provided: start_index={start_index}, end_index={end_index}")
        sys.exit(1)
    
    return start_index, end_index

if __name__ == "__main__":
    start_index, end_index = validate_arguments()
    per_domain_valid_configs = validate_config_ids(start_index,end_index)
    # print(len(per_domain_valid_configs.keys()))