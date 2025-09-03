import os
import re
import sys
import json
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np

unified_dataset = {}
with open('../unified_pixel_dataset.json','r') as f:
    unified_dataset = json.load(f)

parameters_overall_dict = {
    "em" : 0,
    "fn" : 0,
    "ln" : 0,
    "ph" : 0,
    "ge" : 0,
    "zp" : 0,
    "ct" : 0,
    "st" : 0,
    "country" : 0,
    "db" : 0,
    "external_id" : 0
}

rank_bins = {
    0 : (0,100000),
    1 : (100000,200000),
    2 : (200000,300000),
    3 : (300000,400000),
    4 : (400000,500000),
    5 : (500000,600000),
    6 : (600000,700000),
    7 : (700000,800000),
    8 : (800000,900000),
    9 : (900000,1000000)
}


def get_rank_bin(rank, rank_bins):
    for bin_id, (start, end) in rank_bins.items():
        if start <= rank < end:
            return bin_id
    return None

def custom_sort_(parameters):

    sorted_params = []
    for param in parameters_overall_dict.keys():
        if param in parameters:
            sorted_params.append(param)

    return sorted_params
    
per_rank_bins_combinations = dict()
for domain in unified_dataset.keys():
    parameters = unified_dataset[domain]['Parameters']
    rank = unified_dataset[domain]['Rank']
    rank_bin = get_rank_bin(rank,rank_bins)

    filtered_parameters = [item for item in parameters if item != '']

    if (len(filtered_parameters) > 0):
        if rank_bin not in per_rank_bins_combinations.keys():
            per_rank_bins_combinations[rank_bin] = dict()

        sorted_parameters = custom_sort_(filtered_parameters)
        as_str = str(sorted_parameters)

        if as_str not in per_rank_bins_combinations[rank_bin].keys():
            per_rank_bins_combinations[rank_bin][as_str] = 1
        else:
            per_rank_bins_combinations[rank_bin][as_str] += 1
    else:
        if rank_bin not in per_rank_bins_combinations.keys():
            per_rank_bins_combinations[rank_bin] = dict()

        if 'None' not in per_rank_bins_combinations[rank_bin].keys():
            per_rank_bins_combinations[rank_bin]['None'] = 1
        else:
            per_rank_bins_combinations[rank_bin]['None'] += 1



def visualize_rank_bin_combinations(per_rank_bins_combinations, top_n=4):
    all_combinations = {}
    for bin_id, combinations in per_rank_bins_combinations.items():
        for combo, count in combinations.items():
            if combo in all_combinations:
                all_combinations[combo] += count
            else:
                all_combinations[combo] = count

    top_10_combos = sorted(all_combinations.items(), key=lambda x: x[1], reverse=True)[:11]

    for combo in top_10_combos:
        print(f"Combination: {str(combo[0])} | Count: {str(combo[1])}")

    top_combinations = sorted(all_combinations.items(), key=lambda x: x[1], reverse=True)[:top_n]
    top_combo_names = [combo for combo, _ in top_combinations]
    
    bin_labels = {
        0: "1-100K",
        1: "100K-200K",
        2: "200K-300K",
        3: "300K-400K",
        4: "400K-500K",
        5: "500K-600K",
        6: "600K-700K",
        7: "700K-800K",
        8: "800K-900K",
        9: "900K-1M"
    }
    
    plot_data = []
    for bin_id, combinations in per_rank_bins_combinations.items():
        bin_data = {'Bin': bin_labels[bin_id], 'BinID': bin_id}
        bin_total = sum(combinations.values())
        
        for combo_name in top_combo_names:
            if combo_name in combinations:
                percentage = (combinations[combo_name] / bin_total) * 100
                bin_data[combo_name] = percentage
            else:
                bin_data[combo_name] = 0
                
        other_percentage = 100 - sum(bin_data.get(combo, 0) for combo in top_combo_names)
        bin_data['Other'] = other_percentage
        
        plot_data.append(bin_data)
    
    plot_data.sort(key=lambda x: x['BinID'])
    df = pd.DataFrame(plot_data)
    
    plt.figure(figsize=(25, 20))
    
    bottom = np.zeros(len(plot_data))
    bar_width = 0.6
    
    colors = [ '#8B2500', '#FF6B45', '#FFDA8A','#FFFCDD']
    
    if top_n < 4:
        colors = colors[:top_n] + ['#5A5A5A']  
    else:
        colors = colors + ['#5A5A5A']  

    legend_labels = {}
    for i, combo in enumerate(top_combo_names):
        short_label = combo
        if combo == str(list(parameters_overall_dict.keys())):
            short_label = 'All Parameters'
        
        legend_labels[combo] = short_label
    
    for i, combo in enumerate(top_combo_names):
        values = df[combo].values
        plt.bar(df['Bin'], values, bottom=bottom, width=bar_width, label=legend_labels[combo], color=colors[i])
        bottom += values
    
    plt.bar(df['Bin'], df['Other'].values, bottom=bottom, width=bar_width, label="Other", color=colors[-1])
    
    bottom = np.zeros(len(plot_data))
    for combo in top_combo_names + ['Other']:
        values = df[combo].values
        for i, v in enumerate(values):
            plt.text(i, bottom[i] + v/2, f'{v:.1f}%', ha='center', va='center',color='black', fontweight='bold', fontsize=24)
        bottom += values
    
    plt.xticks(fontsize=45, rotation=60)
    plt.yticks(fontsize=45)

    plt.xlabel('Website Rank Range', fontsize=50, fontweight='bold')
    plt.ylabel('Percentage (%)', fontsize=50,fontweight='bold')

    legend = plt.legend(title='Parameter Combinations', fontsize=24)
    plt.setp(legend.get_title(), fontsize=24)
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    
    return plt.gcf()


if __name__ == "__main__" :
    fig = visualize_rank_bin_combinations(per_rank_bins_combinations, top_n=4)
    plt.savefig('parameter_combo_distribution.pdf', dpi=300, bbox_inches='tight')
