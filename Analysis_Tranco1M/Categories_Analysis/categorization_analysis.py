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


per_category_param_count = dict()
for domain in unified_dataset.keys():    
    categories = unified_dataset[domain]['Categories']
    if categories:
        for category in categories:
            if category not in per_category_param_count.keys():
                per_category_param_count[category] = parameters_overall_dict.copy()
        
            for parameter in unified_dataset[domain]['Parameters']:
                if parameter != '':
                    per_category_param_count[category][parameter] += 1
    else:
        if 'Unknown' not in per_category_param_count.keys():
            per_category_param_count['Unknown'] = parameters_overall_dict.copy()
        if unified_dataset[domain]['Parameters']:
            for parameter in unified_dataset[domain]['Parameters']:
                if parameter != '':
                    per_category_param_count['Unknown'][parameter] += 1


per_category_count = dict()
for domain in unified_dataset.keys():
    categories = unified_dataset[domain]['Categories']
    if categories:
        for category in categories:
            if category not in per_category_count.keys():
                per_category_count[category] = 1
            else:
                per_category_count[category] += 1

    else:
        if 'Unknown' in per_category_count.keys():
            per_category_count['Unknown'] += 1
        else:
            per_category_count['Unknown'] = 1

per_category_leaked_count = dict()
for domain in unified_dataset.keys():
    categories = unified_dataset[domain]['Categories']
    if categories:
        params = unified_dataset[domain]['Parameters']
        if params and len(params) > 0:
            if len(params) == 1 and params[0] == '':
                pass
            else:
                for category in categories:
                    if category not in per_category_leaked_count.keys():
                        per_category_leaked_count[category] = 1
                    else:
                        per_category_leaked_count[category] += 1

    else:
        params = unified_dataset[domain]['Parameters']
        if params and len(params) > 0:
            if len(params) == 1 and params[0] == '':
                pass
            else:
                if 'Unknown' in per_category_leaked_count.keys():
                    per_category_leaked_count['Unknown'] += 1
                else:
                    per_category_leaked_count['Unknown'] = 1




ordered_per_category_count = dict(sorted(per_category_count.items(), key=lambda item: item[1],reverse=True))
per_category_param_percentages = dict()
for category in ordered_per_category_count:

    if category not in per_category_param_percentages.keys():
        per_category_param_percentages[category] = parameters_overall_dict.copy()

    for parameter in per_category_param_count[category]:
        if category in per_category_leaked_count:
            per_category_param_percentages[category][parameter] = round(((per_category_param_count[category][parameter]*100)/per_category_leaked_count[category]),2)
        
def create_param_category_heatmap(ordered_per_category_count, per_category_param_percentages):
    data = []
    ordered_params = ["em", "fn", "ln", "ph", "ge", "zp", "ct", "st", "country", "db", "external_id"]
    
    for category in ordered_per_category_count:
        if category in per_category_param_percentages:
            for param in ordered_params:
                percentage = per_category_param_percentages[category].get(param, 0)
                data.append({
                    'Category': category,
                    'Parameter': param,
                    'Percentage': percentage
                })
    
    df = pd.DataFrame(data)
    pivot_df = df.pivot(index='Parameter', columns='Category', values='Percentage')
    
    sorted_categories = sorted(ordered_per_category_count.keys(), key=lambda x: ordered_per_category_count[x], reverse=True)
    
    top_categories = sorted_categories[:10]
    
    valid_categories = [cat for cat in top_categories if cat in pivot_df.columns]
    pivot_df = pivot_df[valid_categories]
    
    pivot_df = pivot_df.reindex(ordered_params)
    
    param_names = {
        "em": "email",
        "ph": "phone_number",
        "fn": "first_name",
        "ln": "last_name",
        "ge": "gender",
        "zp": "ZIP_Code",
        "ct": "city",
        "st": "state",
        "country": "country",
        "db": "birth_day",
        "external_id": "external_id"
    }
    
    plt.figure(figsize=(26, 20))  
    cmap = sns.color_palette("Blues", as_cmap=True)
    
    ax = sns.heatmap(pivot_df, annot=True, cmap=cmap, fmt='.1f', linewidths=.5,annot_kws={'size': 35})
    cbar = ax.collections[0].colorbar
    cbar.ax.tick_params(labelsize=45) 
    cbar.ax.set_ylabel('Percentage (%)', fontsize=50,fontweight='bold')


    modified_labels = []
    for category in valid_categories:
        pct = (ordered_per_category_count[category] / sum(ordered_per_category_count.values())) * 100
        modified_labels.append(f"{category} ({pct:.1f}%)")

    ax.set_xticklabels(modified_labels, rotation=45, ha='right',fontsize=24)

    ax.set_yticklabels([param_names[param] for param in ordered_params], rotation=0, ha='right', fontsize=24)

    plt.subplots_adjust(left=0.2)  
    plt.ylabel('Parameter',  fontsize=50,fontweight='bold')
    plt.xlabel('Website Category',fontsize=50,fontweight='bold')
    plt.xticks(fontsize=45)
    plt.yticks(fontsize=45)
    plt.tight_layout()

    return plt.gcf()

def create_stacked_barplot():
    per_category_pixels = dict()
    for domain in unified_dataset.keys():
        categories = unified_dataset[domain]['Categories']

        if categories:
            for category in categories:
                if category not in per_category_pixels.keys():
                    per_category_pixels[category] = {
                        'total' : 1,
                        'tracking_params' : 0,
                        'not_tracking_params' : 0
                    }
                else:
                    per_category_pixels[category]['total'] += 1
                
                params = unified_dataset[domain]['Parameters']
                if params and len(params) > 0:
                    if len(params) == 1 and params[0] == '':
                        per_category_pixels[category]['not_tracking_params'] += 1
                    else:
                        per_category_pixels[category]['tracking_params'] += 1
                else:
                    per_category_pixels[category]['not_tracking_params'] += 1
        else:
            category = 'Unknown'
            if category not in per_category_pixels.keys():
                per_category_pixels[category] = {
                    'total' : 1,
                    'tracking_params' : 0,
                    'not_tracking_params' : 0
                }
            else:
                per_category_pixels[category]['total'] += 1
            
            params = unified_dataset[domain]['Parameters']
            if params and len(params) > 0:
                if len(params) == 1 and params[0] == '':
                    per_category_pixels[category]['not_tracking_params'] += 1
                else:
                    per_category_pixels[category]['tracking_params'] += 1
            else:
                per_category_pixels[category]['not_tracking_params'] += 1



    for item in per_category_pixels.keys():
        print(f'Category: {item} | Items: {str(per_category_pixels[item])}')
    
    categories = []
    totals = []
    tracking_params = []
    not_tracking_params = []

    for category, data in per_category_pixels.items():
        categories.append(category)
        totals.append(data['total'])
        tracking_params.append(data['tracking_params'])
        not_tracking_params.append(data['not_tracking_params'])

    df = pd.DataFrame({
        'category': categories,
        'total': totals,
        'tracking_params': tracking_params,
        'not_tracking_params': not_tracking_params
    })

    df['tracking_percentage'] = (df['tracking_params'] / df['total'] * 100).round(2)
    df['not_tracking_percentage'] = (df['not_tracking_params'] / df['total'] * 100).round(2)
    df_sorted = df.sort_values('total', ascending=False).head(10)

    plt.figure(figsize=(25, 20))
    x = np.arange(len(df_sorted))
    width = 0.8  

    plt.bar(x, df_sorted['not_tracking_percentage'], width, label='Not Tracking Parameters (%)', color='#E0E0E0')
    plt.bar(x, df_sorted['tracking_percentage'], width, bottom=df_sorted['not_tracking_percentage'], label='Tracking Parameters (%)', color='#2C8BC9')

    total_domains = df['total'].sum()
    modified_labels = []
    for category, total in zip(df_sorted['category'], df_sorted['total']):
        pct = (total / total_domains) * 100
        modified_labels.append(f"{category} ({pct:.1f}%)")

    plt.xlabel('Categories', fontsize=50,fontweight='bold')
    plt.ylabel('Percentage (%)', fontsize=50,fontweight='bold')
    plt.xticks(x, modified_labels, rotation=45, ha='right', fontsize=45)
    plt.yticks(fontsize=45)
    plt.legend(fontsize=33, loc='upper center',bbox_to_anchor=(0.5, 1.018),ncol=3,framealpha=0.8, facecolor='white', edgecolor='lightgray')

    for i, (not_track, track) in enumerate(zip(df_sorted['not_tracking_percentage'], df_sorted['tracking_percentage'])):
        if not_track > 5:  
            plt.text(i, not_track/2, f"{round(not_track,1)}", ha='center', va='center', fontsize=45, color='black',rotation=75)
        
        if track > 5:  
            plt.text(i, not_track + track/2, f"{round(track,1)}", ha='center', va='center', fontsize=45, color='white',rotation=75)

    plt.tight_layout(rect=[0, 0.1, 1, 1])
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.grid(False) 
    plt.ylim(0, 110)

    plt.savefig('per_category_leakage_tendencies.pdf', dpi=300, bbox_inches='tight')


# ======================================================    SENSITIVE CATEGORIES    ===============================================================
sensitive_categories = [
    'Health & Fitness',
    'Politics, Society and Law',
    'Finances',
    'Dating',
    'Pornography & Sexuality',
    'Politics, Society and Law',
    'Religious',
    'Alchohol & Tobacco',
    'Gambling',
    'Education'
]

sensitive_count = 0
for domain in unified_dataset.keys():
    categories = unified_dataset[domain]['Categories']
    if categories:
        for category in categories:
            if category in sensitive_categories:
                sensitive_count += 1
                break

print(f'Total websites under a sensitive category: {sensitive_count}')

sensitive_per_category_count = {k: v for k, v in ordered_per_category_count.items() if k in sensitive_categories}
sensitive_per_category_param_percentages = {k: v for k, v in per_category_param_percentages.items() if k in sensitive_categories}
sorted_sensitive_categories = sorted(sensitive_per_category_count.keys(), key=lambda x: sensitive_per_category_count[x], reverse=True)


def create_sensitive_param_category_heatmap(sensitive_per_category_count, sensitive_per_category_param_percentages):
    data = []
    ordered_params = ["em", "fn", "ln", "ph", "ge", "zp", "ct", "st", "country", "db", "external_id"]
    
    for category in sorted_sensitive_categories:
        if category in sensitive_per_category_param_percentages:
            for param in ordered_params:
                percentage = sensitive_per_category_param_percentages[category].get(param, 0)
                data.append({
                    'Category': category,
                    'Parameter': param,
                    'Percentage': percentage
                })
    
    df = pd.DataFrame(data)
    pivot_df = df.pivot(index='Parameter', columns='Category', values='Percentage')
    
    valid_categories = [cat for cat in sorted_sensitive_categories if cat in pivot_df.columns]
    pivot_df = pivot_df[valid_categories]
    
    pivot_df = pivot_df.reindex(ordered_params)
    
    param_names = {
        "em": "email",
        "ph": "phone_number",
        "fn": "first_name",
        "ln": "last_name",
        "ge": "gender",
        "zp": "ZIP_Code",
        "ct": "city",
        "st": "state",
        "country": "country",
        "db": "birth_day",
        "external_id": "external_id"
    }
    
    plt.figure(figsize=(26, 20))  
    cmap = sns.color_palette("Blues", as_cmap=True)
    ax = sns.heatmap(pivot_df, annot=True, cmap=cmap, fmt='.1f', linewidths=.5, annot_kws={'size': 35}, cbar_kws={'label': 'Percentage (%)'})
    
    cbar = ax.collections[0].colorbar
    
    for tick in cbar.ax.get_yticklabels():
        tick.set_fontsize(45)
    
    cbar.ax.set_ylabel('Percentage (%)', fontsize=50, fontweight='bold')
    total_websites = sum(ordered_per_category_count.values())
    
    modified_labels = []
    for category in valid_categories:
        pct = (ordered_per_category_count[category] / total_websites) * 100
        modified_labels.append(f"{category} ({pct:.1f}%)")

    ax.set_xticklabels(modified_labels, rotation=45, ha='right', fontsize=45)
    ax.set_yticklabels([param_names[param] for param in ordered_params], rotation=0, ha='right', fontsize=45)

    plt.ylabel('Parameter', fontsize=50, fontweight='bold')
    plt.xlabel('Sensitive Website Category', fontsize=50, fontweight='bold')
    
    plt.subplots_adjust(left=0.2)  
    plt.tight_layout()

    return plt.gcf()


def create_sensitive_stacked_bar_plot():

    sensitive_tracking_data = {}

    for category in sensitive_categories:
        if category in per_category_count:
            total = per_category_count[category]
            tracking = per_category_leaked_count.get(category, 0)
            not_tracking = total - tracking
            
            sensitive_tracking_data[category] = {
                'total': total,
                'tracking_params': tracking,
                'not_tracking_params': not_tracking
            }

    categories = []
    totals = []
    tracking_params = []
    not_tracking_params = []

    for category, data in sensitive_tracking_data.items():
        categories.append(category)
        totals.append(data['total'])
        tracking_params.append(data['tracking_params'])
        not_tracking_params.append(data['not_tracking_params'])

    df_sensitive = pd.DataFrame({
        'category': categories,
        'total': totals,
        'tracking_params': tracking_params,
        'not_tracking_params': not_tracking_params
    })

    df_sensitive['tracking_percentage'] = (df_sensitive['tracking_params'] / df_sensitive['total'] * 100).round(2)
    df_sensitive['not_tracking_percentage'] = (df_sensitive['not_tracking_params'] / df_sensitive['total'] * 100).round(2)

    df_sorted_sensitive = df_sensitive.sort_values('total', ascending=False)

    plt.figure(figsize=(25, 20))
    x = np.arange(len(df_sorted_sensitive))
    width = 0.8

    plt.bar(x, df_sorted_sensitive['not_tracking_percentage'], width, label='Not Tracking Parameters (%)', color='#E0E0E0')
    plt.bar(x, df_sorted_sensitive['tracking_percentage'], width, bottom=df_sorted_sensitive['not_tracking_percentage'], label='Tracking Parameters (%)', color='#2C8BC9')

    total_domains = sum(ordered_per_category_count.values())
    modified_labels = []
    for category, total in zip(df_sorted_sensitive['category'], df_sorted_sensitive['total']):
        pct = (total / total_domains) * 100
        modified_labels.append(f"{category} ({pct:.1f}%)")

    
    plt.xlabel('Categories', fontsize=50,fontweight='bold')
    plt.ylabel('Percentage (%)', fontsize=50,fontweight='bold')
    plt.xticks(x, modified_labels, rotation=45, ha='right', fontsize=45)
    plt.yticks(fontsize=24)
    plt.legend(fontsize=33, loc='upper center',bbox_to_anchor=(0.5, 1.018),ncol=3,framealpha=0.8, facecolor='white', edgecolor='lightgray')



    for i, (not_track, track) in enumerate(zip(df_sorted_sensitive['not_tracking_percentage'], df_sorted_sensitive['tracking_percentage'])):
        if not_track > 5:
            plt.text(i, not_track/2, f"{round(not_track,1)}", ha='center', va='center', fontsize=45, color='black', fontweight='bold',rotation=75)
        
        if track > 5:
            plt.text(i, not_track + track/2, f"{round(track,1)}", ha='center', va='center', fontsize=45, color='white', fontweight='bold', rotation=75)

    plt.tight_layout(rect=[0, 0.1, 1, 1])
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.grid(False)
    plt.ylim(0, 110)

    plt.savefig('sensitive_categories_tracking_tendencies.pdf', dpi=300, bbox_inches='tight')








if __name__ == "__main__":

    fig = create_param_category_heatmap(ordered_per_category_count, per_category_param_percentages)
    plt.savefig('parameter_tracking_heatmap.pdf', dpi=300, bbox_inches='tight')
    create_stacked_barplot()    


    fig = create_sensitive_param_category_heatmap(sensitive_per_category_count, sensitive_per_category_param_percentages)
    plt.savefig('sensitive_categories_parameter_tracking_heatmap.pdf', dpi=300, bbox_inches='tight')
    create_sensitive_stacked_bar_plot()