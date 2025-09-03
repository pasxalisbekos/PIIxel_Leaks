import os
import re
import sys
import json

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from matplotlib.ticker import FixedLocator
from tabulate import tabulate



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


def plot_pixel_adoption_by_rank(fbpixel_websites, tranco_domains):
    # sns.set_style("whitegrid")
    
    pixel_domains_with_ranks = {}
    for domain in fbpixel_websites:
        if domain in tranco_domains:
            pixel_domains_with_ranks[domain] = tranco_domains[domain]
    
    print(f"Total Facebook Pixel domains: {len(fbpixel_websites)}")
    print(f"Domains with ranking information: {len(pixel_domains_with_ranks)}")
    
    if not pixel_domains_with_ranks:
        print("No domains with ranking found. Check domain format consistency.")
        return
    
    df_ranks = pd.DataFrame({
        'domain': list(pixel_domains_with_ranks.keys()),
        'rank': list(pixel_domains_with_ranks.values())
    })
    
    brackets = [
        (1, 10000, "0-10K"),
        (10001, 20000, "10K-20K"),
        (20001, 50000, "20K-50K"),
        (50001, 100000, "50K-100K"),
        (100001, 200000, "100K-200K"),
        (200001, 500000, "200K-500K"),
        (500001, 1000000, "500K-1M")
    ]
    
    def assign_bracket(rank):
        for min_rank, max_rank, label in brackets:
            if min_rank <= rank <= max_rank:
                return label
        return "Other"
    
    df_ranks['bracket'] = df_ranks['rank'].apply(assign_bracket)
    
    adoption_rates = []
    labels = []
    for min_rank, max_rank, label in brackets:
        total_in_bracket = max_rank - min_rank + 1
        with_pixel = len(df_ranks[(df_ranks['rank'] >= min_rank) & (df_ranks['rank'] <= max_rank)])
        adoption_rate = (with_pixel / total_in_bracket) * 100
        adoption_rates.append(adoption_rate)
        labels.append(label)
    
    fig, ax = plt.subplots(figsize=(24, 17))
    dark_blue = 'royalblue'
    
    bars = ax.bar(labels, adoption_rates, color=dark_blue)
    for i, rate in enumerate(adoption_rates):
        ax.text(i, rate + 0.5, f"{rate:.2f}%", ha='center', fontsize=45, fontweight='bold')
    
    ax.set_ylim(0, 30)    
    ax.set_xlabel("Website Ranking Bracket", fontsize=50, fontweight='bold')
    ax.set_ylabel("Meta's Pixel Adoption Rate (%)", fontsize=50, fontweight='bold')

    plt.xticks(fontsize=45, rotation=45)
    plt.yticks(fontsize=45)
    
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout(rect=[0, 0.03, 1, 0.97])  
    plt.savefig("facebook_pixel_adoption_by_rank.pdf", dpi=300)
    plt.show()



def filter_top_10k_domains_EC2(items_dict, tranco_domains):
    top_10k = {}
    
    for domain in items_dict:
        if domain in tranco_domains and tranco_domains[domain] <= 10000:
            top_10k[domain] = items_dict[domain]
    
    print(f"Total domains: {len(items_dict)}")
    print(f"Domains in top 10K: {len(top_10k)}")
    
    return top_10k


def get_domains_dynamic_found(dynamic_folder):
    fbp_domains = []
    for path, subdirs, files in os.walk(dynamic_folder):
        for name in files:
            if name.endswith("_config_urls.json"):
                temp_path = os.path.join(path,name)
                # print(temp_path)
                temp = []
                with open(temp_path,"r") as f:
                    temp = json.load(f)
                # total += (len(list(set(temp.keys()))))
                    for key in temp.keys():
                        fbp_domains.append(key.replace('www.',''))

    for path, subdirs, files in os.walk(dynamic_folder):
        for name in files:
            if name.endswith("_report_urls.json"):
                temp_path = os.path.join(path,name)
                # print(temp_path)
                temp = []
                with open(temp_path,"r") as f:
                    temp = json.load(f)
                # total += (len(list(set(temp.keys()))))
                    for key in temp.keys():
                        if key.replace('www.','') not in fbp_domains:
                            fbp_domains.append(key.replace('www.',''))

    fbp_domains = list(set(fbp_domains))
    return fbp_domains





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

    headless_only = dict()
    for path, subdirs, files in os.walk(directory_path):
        for name in files:
            if name.endswith("state_fbq.json"):
                temp_path = os.path.join(path,name)
                # print(temp_path)
                with open(temp_path,'r') as f:
                    temp_domains = json.load(f)
                    for domain in temp_domains:
                        if domain not in headless_only.keys():
                            headless_only[domain] = temp_domains[domain]
    


    return static_only, headless_only


def EC2_10K_analysis():
    static_only, headless_only = get_domains_static_found('../RESULTS_EC2')

    top10K_ec2 = filter_top_10k_domains_EC2(fbpixel_websites, tranco_domains)
    top10K_dynamic = get_domains_dynamic_found('../../Consecutive_Runs/Dynamic')

    not_in_static = []
    for domain in top10K_dynamic:
        if domain not in top10K_ec2.keys():
            not_in_static.append(domain)


    not_in_total = []
    for domain in not_in_static:
        if domain not in static_only.keys() and domain not in headless_only.keys():
            not_in_total.append(domain)


    static_only, headless_only = get_domains_static_found('../../Consecutive_Runs/Static/')
    not_in_total_ec2 = []
    for domain in not_in_static:
        if domain not in static_only.keys() and domain not in headless_only.keys():
            not_in_total_ec2.append(domain)

    print('-------------------------------------------------------------------------------------------------------------------------------------')
    print(f'\t Domains in 10K not found in Static EC2: {len(not_in_static)} (after validation and cleanup)')
    print(f'\t Domains in 10K not found in Static EC2: {len(not_in_total)} (before validation and cleanup)')
    print(f'\t Domains in 10K not found in Static EC2: {len(not_in_total_ec2)} (excluding domains found locally)')
    print('-------------------------------------------------------------------------------------------------------------------------------------')



def get_implementation_statistics(fbpixel_websites):
    per_case_pixels = dict()
    per_case_pixels_high_level = dict()
    for domain in fbpixel_websites.keys():
        types = fbpixel_websites[domain]['Pixel_Types']

        key = ''
        for type_ in types:

            if type_ == 'LIGHTWEIGHT_PIXEL' or type_ == 'BASECODE_PIXEL':
                key = 'Static.Meta_Pixel'
            elif type_ == 'HEADLESS.FBP':
                key = 'Dynamic.Meta_Pixel'
            elif type_ == 'PIXEL_IN_OTHER_TP':
                key = 'Static.Other_TP'
            elif type_ == 'HEADLESS.GTM':
                key = 'Dynamic.GTM'
            else:
                key = 'Static.'+type_


            if key not in per_case_pixels.keys():
                per_case_pixels[key] = 1
            else:
                per_case_pixels[key] += 1
            
            if 'Static.GTM_' in key:
                key = 'Static.GTM'

            if key not in per_case_pixels_high_level.keys():
                per_case_pixels_high_level[key] = 1
            else:
                per_case_pixels_high_level[key] += 1        
            break

    total_pixels = sum(per_case_pixels.values())
    sorted_pixels = sorted(per_case_pixels.items(), key=lambda x: x[1], reverse=True)
    print('------------------- HIGH LEVEL ------------------')
    sorted_pixels = sorted(per_case_pixels_high_level.items(), key=lambda x: x[1], reverse=True)
    table_data = [[key, value] for key, value in sorted_pixels]
    headers = ["Implementation type", "Website count"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    


if __name__ == "__main__":

    fbpixel_websites = {}
    with open('../unified_pixel_dataset.json','r') as f:
        fbpixel_websites = json.load(f)


    get_implementation_statistics(fbpixel_websites)
    tranco_domains = dict()
    for domain in fbpixel_websites.keys():
        if domain not in tranco_domains.keys():
            tranco_domains[domain] = fbpixel_websites[domain]['Rank']


    df_analysis = plot_pixel_adoption_by_rank(fbpixel_websites, tranco_domains)

