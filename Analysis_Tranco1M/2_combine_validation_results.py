import os
import json
import re
import sys





def get_domains_static_found(directory_path):
    valid_configs = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.startswith("valid_config_ids"):
                temp_path = os.path.join(path,name)
                print(temp_path)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in valid_configs.keys():
                            if  len(temp_domains[domain]) > 0:
                                valid_configs[domain] = temp_domains[domain]
    return valid_configs


valid_configs = get_domains_static_found('./Validation_Results')

with open('./Results/Clean/valid_config_ids.json', 'w') as f:
    json.dump(valid_configs, f, indent=4)
    f.close()