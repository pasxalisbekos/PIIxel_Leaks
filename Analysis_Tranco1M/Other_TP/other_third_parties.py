import os
import re
import sys
import json

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from urllib.parse import urlparse
import requests
from tabulate import tabulate




fbpixel_websites = {}
with open('../unified_pixel_dataset.json','r') as f:
    fbpixel_websites = json.load(f)
    f.close()

def get_domains_static_found(directory_path):
    static_only = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.endswith("pixels_found.json"):
                temp_path = os.path.join(path,name)
                # print(temp_path)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in static_only.keys():
                            static_only[domain] = temp_domains[domain]


    return static_only

def extract_hostname(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc

def plot_bar_chart(data_dict):
    sorted_dict = dict(sorted(data_dict.items(), key=lambda item: item[1], reverse=True))
    grouped_dict = {}
    custom_sum = 0
    total_sum = sum(data_dict.values())
    
    for key, value in sorted_dict.items():
        if value < 5:
            custom_sum += value
        else:
            grouped_dict[key] = value
    
    if custom_sum > 0:
        grouped_dict['Custom'] = custom_sum


    sorted_grouped = dict(sorted(grouped_dict.items(), key=lambda item: item[1], reverse=True))    
    
    fig, ax = plt.subplots(figsize=(28, 24))
    keys = list(sorted_grouped.keys())
    values = list(sorted_grouped.values())
    
    bars = ax.bar(keys, values, color='royalblue')
    ax.set_yscale('log')
    
    for bar in bars:
        height = bar.get_height()
        percentage = height * 100 / total_sum
        ax.text(bar.get_x() + bar.get_width()/2, height*1.05, f'{percentage:.1f}%', ha='center', fontsize=35)
    
    ax.set_ylabel('Number of websites', fontsize=50)
    ax.set_xlabel('Third Party Service', fontsize=50)
    ax.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.xticks(fontsize=45, rotation=45, ha='right')
    plt.yticks(fontsize=45)
    
    plt.tight_layout()
    plt.savefig('distribution_plot.pdf', dpi=300, bbox_inches='tight')
    
    return plt.gcf()



if __name__ == "__main__":

    static_only = get_domains_static_found('../RESULTS_EC2/')
    clean_static = dict()
    for domain in static_only.keys():
        if domain in fbpixel_websites.keys():
            clean_static[domain] = static_only[domain]

    on_other_tp = dict()
    for domain in clean_static.keys():
        type_ = list(clean_static[domain].keys())[0]
        if type_ == 'PIXEL_IN_OTHER_TP':
            on_other_tp[domain] = clean_static[domain]




    print(f'Total Pixels found implemented by different Third Party Scripts: {len(on_other_tp)}')
    per_tp_implementation = dict()
    per_tp_domains = dict()

    for domain in on_other_tp.keys():
        item = on_other_tp[domain]

        temp_tp = []
        for key in item.keys():
            implementations = item[key]['implementations']
            for implementation in implementations:
                script_url = implementation['script_url']
                host_name_tp = extract_hostname(script_url)
                if host_name_tp not in temp_tp:
                    temp_tp.append(host_name_tp)
        temp_tp = list(set(temp_tp))

        for host_name in temp_tp:
            if host_name not in per_tp_implementation.keys():
                per_tp_implementation[host_name] = 1
            else:
                per_tp_implementation[host_name] += 1

            if host_name not in per_tp_domains.keys():
                per_tp_domains[host_name] = list()
            per_tp_domains[host_name].append(domain)


    try:
        per_tp_implementation = dict(sorted(
            per_tp_implementation.items(), 
            key=lambda item: int(item[1]), 
            reverse=True
        ))
    except Exception as e:
        print(f"Error during sorting: {e}")

    plot_bar_chart(per_tp_implementation)
    with open('./per_third_party_script_domains.json', 'w') as f:
        json.dump(per_tp_domains, f, indent=4)
        f.close()


