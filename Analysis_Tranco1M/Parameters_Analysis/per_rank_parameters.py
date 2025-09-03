import os
import re
import sys
import json

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

fbpixel_websites = {}
with open('../unified_pixel_dataset.json','r') as f:
    fbpixel_websites = json.load(f)
    f.close()

print(f'Total validated websites implementing Pixel: {len(fbpixel_websites)}')

def plot_parameter_adoption_bars(params_dict, tranco_domains):
    all_params = [
        "em", "fn", "ln", "ph", "ge", "zp", 
        "ct", "st", "country", "db", "external_id"
    ]
    
    rank_bins = [
        (0, 100000),
        (100000, 200000),
        (200000, 300000),
        (300000, 400000),
        (400000, 500000),
        (500000, 600000),
        (600000, 700000),
        (700000, 800000),
        (800000, 900000),
        (900000, 1000000)
    ]
    
    bin_labels = [f"{start//1000}K-{end//1000}K" for start, end in rank_bins]
    param_counts = {param: {label: 0 for label in bin_labels} for param in all_params}
    
    for domain, params in params_dict.items():
        if domain in tranco_domains:
            rank = tranco_domains[domain]
            for i, (start, end) in enumerate(rank_bins):
                if start <= rank < end:
                    bin_label = bin_labels[i]
                    for param in params:
                        if param in all_params:
                            param_counts[param][bin_label] += 1
                    break
    
    df = pd.DataFrame({param: [param_counts[param][bin] for bin in bin_labels] for param in all_params})
    df.index = bin_labels
    
    fig, ax = plt.subplots(figsize=(24, 15))
    
    n_bins = len(bin_labels)
    n_params = len(all_params)
    width = 0.7 / n_params
    
    param_totals = {param: df[param].sum() for param in all_params}
    sorted_params = sorted(all_params, key=lambda x: param_totals[x], reverse=True)
    
    blues = plt.cm.Blues(np.linspace(0.9, 0.3, len(sorted_params)))
    
    for i, param in enumerate(sorted_params):
        if param_totals[param] > 0:
            x = np.arange(n_bins) + (i - n_params/2 + 0.5) * width
            ax.bar(x, df[param], width, label=f"{param} ({round((param_totals[param]*100)/len(params_dict.keys()),2)} %)",color=blues[i])
    
    ax.set_xticks(np.arange(n_bins))
    ax.set_xticklabels(bin_labels, rotation=45)
    ax.set_xlabel('Website Rank Range', fontsize=50,fontweight='bold')
    ax.set_ylabel('Number of Websites', fontsize=50,fontweight='bold')
    ax.legend(fontsize=30, loc='lower center',bbox_to_anchor=(0.5, 0.05),ncol=3,framealpha=0.8, facecolor='white', edgecolor='lightgray')

    

    plt.xticks(fontsize=45)
    plt.yticks(fontsize=45)
    plt.tight_layout(rect=[0, 0.1, 1, 1])
    plt.grid(axis='y', linestyle='--', alpha=0.3)

    plt.savefig('parameter_adoption_per_rank.pdf', dpi=300, bbox_inches='tight')
    
    return df



if __name__ == "__main__":

    params_clean = dict()
    tranco_domains = dict()
    for domain in fbpixel_websites.keys():
        params = fbpixel_websites[domain]['Parameters']
        if len(params) > 0:
            if len(params) == 1 and params[0] == '':
                pass
            else:
                params_clean[domain] = params
                if domain not in tranco_domains.keys():
                    tranco_domains[domain] = fbpixel_websites[domain]['Rank']

    print(f'Total websites tracking at least one parameter: {len(params_clean)} (65.45%)')
    df_params = plot_parameter_adoption_bars(params_clean, tranco_domains)