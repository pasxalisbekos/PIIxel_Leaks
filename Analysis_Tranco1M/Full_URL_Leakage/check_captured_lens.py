import os
import re
import sys
import json
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from urllib.parse import urlparse
from matplotlib.gridspec import GridSpec
import csv
import tldextract
import collections
from tabulate import tabulate


def extract_hostname(url):
    parsed_url = urlparse(url)
    return parsed_url.netloc



path = './FullURL_results'


domains_processed = []
categories_dict = {
    'news' : {},
    'politics_and_law' : {},
    'ecommerce': {},
    'shopping' : {},
    'health' : {},
    'real_estate': {},
    'education' : {}
}




unreachable = dict()
erroneous = dict()
timed_out = list()
explored = dict()
unique_domains = []



nav_logs_total = dict()
single_visitation_only = []
raised_error_before_exploration = []
no_pixel_requests = []
no_captured_requests_on_subpages = []
no_navigation_log = []
not_pixel_activity = []


re_runs = []

def get_results(category_type):

    towards_analysis = dict()
    for path, subdirs, files in os.walk('./FullURL_results'):
            for name in files:
                temp_path = os.path.join(path,name)

                if temp_path.endswith("_errors.json") and category_type in temp_path:
                    data = []   
                    with open(temp_path,'r') as f:
                        data = json.load(f)
                        f.close()
                    
                    for domain in data.keys():
                        if domain not in erroneous.keys():
                            erroneous[domain] = data[domain]


                if temp_path.endswith("_unreachable_websites.json") and category_type in temp_path:
                    data = []
                    with open(temp_path,'r') as f:
                        data = json.load(f)
                        f.close()

                    for domain in data.keys():
                        if domain not in unreachable.keys():
                            unreachable[domain] = data[domain]
                    

                if temp_path.endswith("timeouts.json") and category_type in temp_path:
                    data = []
                    with open(temp_path,'r') as f:
                        data = json.load(f)
                        for domain in data.keys():
                            timed_out.append(domain)
                        f.close()

                
                if temp_path.endswith("_total_full_urls.json") and category_type in temp_path:
                    data = []
                    print(temp_path)
                    with open(temp_path,'r') as f:
                        data = json.load(f)
                        f.close()

                    for domain in data.keys():
                        if domain not in explored.keys():
                            explored[domain] = data[domain]

    for domain in explored.keys():
        towards_analysis[domain] = explored[domain]


    for domain in towards_analysis.keys():
        domain = urlparse(domain).netloc
        unique_domains.append(domain)

    return towards_analysis

def get_all_dls_rls(item):
    
    rls = list()
    dls = list()
    fbpixel_url = ''
    for request_item in item:
        params = request_item['params']
        if('rl' in params.keys() and 'dl' in params.keys()):
            dls.append(params['dl'])
            rls.append(params['rl'])
            fbpixel_url = request_item["URL"]

    return list(set(rls)), list(set(dls)), fbpixel_url


def handle_complete_navigation(nav_log, requests_captured_per_subpage, website):

    journey_depth = 0
    temp_nav_log = []

    found_at_least_one = 0

    for i in range(len(nav_log)):
        item = nav_log[i]
        if("url" in item.keys()):
            pass
        else:
            if ("error" in item.keys()):
                break
            else:
                prev_url = item['current_page_info']['referrer']
                curr_url = item['current_page_info']['current_url']
                if (curr_url in requests_captured_per_subpage.keys()):
                    found_at_least_one = 1
                    curr_page_item = requests_captured_per_subpage[curr_url]
                    
                    rls, dls, fbpixel_url = get_all_dls_rls(curr_page_item)
                    item['rls'] = rls
                    item['dls'] = dls
                    item['Pixel URL'] = fbpixel_url

                    temp_nav_log.append(item)
                else:
                    pass

    return temp_nav_log


no_pixel_requests_on_subpages = []
second_visitation_raised_error = []

def get_analytics(towards_analysis):
    total_websites = len(towards_analysis.keys())
    no_navigation_log = []
    no_pixel_requests = []
    single_visitation_only = []
    raised_error_before_exploration = []
    second_visitation_raised_error = []
    not_pixel_activity = []
    nav_logs_total = {}
    
    categorized_websites = set()
    
    for website in towards_analysis.keys():
        values = towards_analysis[website]
        
        if website in categorized_websites:
            continue
            
        if 'navigation_log' not in values.keys():
            no_navigation_log.append(towards_analysis[website])
            categorized_websites.add(website)
            continue

        nav_log = values['navigation_log']
        
        requests_captured_per_subpage = dict()
        for key in values.keys():
            if key != 'navigation_log':
                requests_captured_per_subpage[key] = values[key]

        visited_path_len = len(requests_captured_per_subpage.keys())

        if visited_path_len == 0:
            no_pixel_requests.append(website)
            categorized_websites.add(website)
            continue
        
        if len(nav_log) > 0 and ("error" in nav_log[0].keys()):
            raised_error_before_exploration.append(website)
            categorized_websites.add(website)
            continue
            
        if len(nav_log) > 1 and ("error" in nav_log[1].keys()):
            second_visitation_raised_error.append(towards_analysis[website])
            categorized_websites.add(website)
            continue
            
        if visited_path_len == 1 or len(nav_log) == 1:
            single_visitation_only.append(towards_analysis[website])
            categorized_websites.add(website)
            continue
        
        temp_nav_log = handle_complete_navigation(nav_log, requests_captured_per_subpage, website)
        if len(temp_nav_log) > 0:
            nav_logs_total[website] = temp_nav_log
            categorized_websites.add(website)
        else:
            not_pixel_activity.append(towards_analysis[website])
            categorized_websites.add(website)

    categorized_count = len(categorized_websites)
    
    table_data = [
        ["Total websites crawled:", total_websites],
        ["At least one navigated path tracked:", len(nav_logs_total.keys())],
        ["No pixel requests captured:", len(no_pixel_requests)],
        ["Single visitation page:", len(single_visitation_only)],
        ["Raised error before exploration:", len(raised_error_before_exploration)],
        ["Raised error on the second page (timeout):", len(second_visitation_raised_error)],
        ["Could not capture navigation log:", len(no_navigation_log)],
        ["No Pixel activity for current URL:", len(not_pixel_activity)],
        ["Total categorized websites:", categorized_count],
        ["Verification (should be 0):", total_websites - categorized_count]
    ]
    print(tabulate(table_data, headers=["Description", "Count"], tablefmt="grid"))

    
    return {
        "total_websites" : total_websites,
        "nav_logs_total": nav_logs_total,
        "no_pixel_requests": no_pixel_requests,
        "single_visitation_only": single_visitation_only,
        "raised_error_before_exploration": raised_error_before_exploration,
        "second_visitation_raised_error": second_visitation_raised_error,
        "no_navigation_log": no_navigation_log,
        "not_pixel_activity": not_pixel_activity
    }



def reset_globals():
    global unreachable,erroneous,timed_out,explored,unique_domains,nav_logs_total,single_visitation_only,raised_error_before_exploration,no_pixel_requests,no_captured_requests_on_subpages,no_captured_requests_on_subpages,not_pixel_activity,no_navigation_log

    unreachable = dict()
    erroneous = dict()
    timed_out = list()
    explored = dict()
    unique_domains = []



    nav_logs_total = dict()
    single_visitation_only = []
    raised_error_before_exploration = []
    no_pixel_requests = []
    no_captured_requests_on_subpages = []
    no_navigation_log = []
    not_pixel_activity = []



def plot_per_cat(per_category_results):

    original_crawled = 2000  
    categories = list(per_category_results.keys())
    total_websites = [per_category_results[cat]['total_websites'] for cat in categories]
    nav_logs_total = [per_category_results[cat]['nav_logs_total'] for cat in categories]

    kept_percentages = [round(total/original_crawled*100, 1) for total in total_websites]
    journey_percentages = [round(nav/total*100, 1) for nav, total in zip(nav_logs_total, total_websites)]

    print("\nStatistics Table:")
    stats_table = []
    for cat, kept, journey in zip(categories, kept_percentages, journey_percentages):
        stats_table.append([cat.replace('_', ' ').title(), f"{kept}%", f"{journey}%"])
    
    print(tabulate(stats_table, headers=["Category", "Kept from 2000", "With Full Journey"],tablefmt="grid"))

    fig = plt.figure(figsize=(14, 8))
    ax = fig.add_subplot(111)
    bar_width = 0.35
    x = np.arange(len(categories))
    bars1 = ax.bar(x - bar_width/2, total_websites, bar_width, label='Websites Sharing at Least One Full URL', color='#3a86ff')

    bars2 = ax.bar(x + bar_width/2, nav_logs_total, bar_width,label='Websites Sharing Full Browsing Journey', color='#8338ec')

    for bar in bars1:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 20, f'{int(height)}', ha='center', fontsize=9)

    for bar in bars2:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 20, f'{int(height)}', ha='center', fontsize=9)

    for i in range(len(categories)):
        ax.text(i, -100, f'Kept: {kept_percentages[i]}%\nJourney: {journey_percentages[i]}%', ha='center', fontsize=9, fontweight='bold')

    ax.set_title('Number of Websites Sharing URLs vs Full Browsing Journey by Category', fontsize=16)
    ax.set_xlabel('Website Categories', fontsize=14)
    ax.set_ylabel('Number of Websites', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels([cat.replace('_', ' ').title() for cat in categories])
    ax.legend(loc='upper right', fontsize=12)
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    ax.set_ylim(-150, max(total_websites) * 1.1)

    plt.tight_layout()
    plt.savefig('website_sharing_comparison.pdf', dpi=300, bbox_inches='tight')
    plt.show()

    print("\nDetailed Statistics:")
    detailed_table = []
    for i, cat in enumerate(categories):
        detailed_table.append([
            cat.replace('_', ' ').title(), 
            original_crawled, 
            total_websites[i], 
            f"{kept_percentages[i]}%", 
            nav_logs_total[i], 
            f"{journey_percentages[i]}%"
        ])
    
    print(tabulate(detailed_table, headers=["Category", "Original", "Kept", "Kept %", "With Journey", "Journey %"],tablefmt="grid"))

    avg_kept = sum(total_websites) / len(total_websites)
    avg_journey = sum(nav_logs_total) / len(nav_logs_total)
    avg_kept_pct = sum(kept_percentages) / len(kept_percentages)
    avg_journey_pct = sum(journey_percentages) / len(journey_percentages)

    print("\nAverages:")
    averages_table = [
        ["Average kept websites", f"{avg_kept:.1f}", f"({avg_kept_pct:.1f}% of original)"], 
        ["Average websites with journey", f"{avg_journey:.1f}", f"({avg_journey_pct:.1f}% of kept)"]
    ]
    print(tabulate(averages_table, tablefmt="grid"))





def check_pii_leakage_with_URL_leakage(domains):

    unified_dataset = {}
    with open('../unified_pixel_dataset.json','r') as f:
        unified_dataset = json.load(f)
    f.close()

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

    not_found_in_unified = 0

    unique_PII = 0
    for domain in domains:
        domain_name = domain.replace('https://','').replace('http://','')
        domain_name = domain_name.split('/')[0]
        if domain_name not in unified_dataset.keys():
            temp_dom = domain_name.replace('www.','')
            if temp_dom not in unified_dataset.keys():
                not_found_in_unified += 1
            else:
                tracked_once = 0
                params = unified_dataset[temp_dom]['Parameters']
                for param in params:
                    if param in parameters_overall_dict.keys():
                        if param == 'em' or param =='ph':
                            if tracked_once == 0:
                                unique_PII += 1
                                tracked_once = 1

                        parameters_overall_dict[param] += 1
        else:
            params = unified_dataset[domain_name]['Parameters']
            tracked_once = 0
            for param in params:
                if param in parameters_overall_dict.keys():
                    if param == 'em' or param =='ph':
                        if tracked_once == 0:
                            unique_PII += 1
                            tracked_once = 1

                    parameters_overall_dict[param] += 1
    
    print(f'At least one unique PII: {unique_PII}')
    return parameters_overall_dict



def create_pii_heatmap(per_category_url_n_params, save_path):
    parameter_order = [
        "em", "fn", "ln", "ph", "ge", "zp", 
        "ct", "st", "country", "db", "external_id"
    ]
    
    parameter_labels = {
        "em": "email",
        "fn": "first_name",
        "ln": "last_name",
        "ph": "phone_number",
        "ge": "gender",
        "zp": "Zip Code",
        "ct": "city",
        "st": "state",
        "country": "country",
        "db": "birth_day",
        "external_id": "external_id"
    }
    
    category_labels = {
        "news": "News",
        "politics_and_law": "Politics & Law",
        "ecommerce": "E-Commerce",
        "shopping": "Shopping",
        "health": "Health",
        "real_estate": "Real Estate",
        "education": "Education"
    }
    
    categories = list(per_category_url_n_params.keys())
    heatmap_data = []
    
    for category in categories:
        category_data = per_category_url_n_params[category]
        total = category_data['total']
        
        for pii_type in parameter_order:
            if pii_type in category_data['param_distr']:
                pii_count = category_data['param_distr'][pii_type]
                percentage = (pii_count / total) * 100 if total > 0 else 0
                heatmap_data.append({
                    'Category': category_labels.get(category, category)+f'\n URL Leakage: {round((total/2000)*100,2)}%',  
                    'PII Type': parameter_labels.get(pii_type, pii_type), 
                    'Raw PII Type': pii_type,  
                    'Percentage': percentage
                })
    
    df = pd.DataFrame(heatmap_data)
    pii_type_ordered = [parameter_labels.get(p, p) for p in parameter_order]
    heatmap_matrix = df.pivot(index='PII Type', columns='Category', values='Percentage')
    heatmap_matrix = heatmap_matrix.reindex(pii_type_ordered)
    
    plt.figure(figsize=(26, 20))
    
    ax = sns.heatmap(heatmap_matrix, annot=True, fmt='.1f', cmap='Blues',linewidths=0.5,cbar_kws={'label': 'Percentage (%)'},annot_kws={'fontsize': 35})
    cbar = ax.collections[0].colorbar    
    for tick in cbar.ax.get_yticklabels():
        tick.set_fontsize(45)
    
    cbar.ax.set_ylabel('Percentage (%)', fontsize=50, fontweight='bold')

    plt.xlabel('Category', fontsize=50, fontweight='bold')
    plt.ylabel('Parameter', fontsize=50, fontweight='bold')
    plt.xticks(rotation=45, ha='right',fontsize=45)
    plt.yticks(rotation=0,fontsize=45)
    plt.tight_layout()
    
    plt.savefig('URL_leakage_with_PII_leakage.pdf', dpi=300, bbox_inches='tight')
    
    return plt.gcf()






























if __name__ == "__main__":


    per_category_url_n_params = dict()
    per_category_results = dict()
    for category in categories_dict.keys():
        print('================================================================================================================')
        towards_analysis = get_results(category)

        # print(towards_analysis.keys())

        analytics = get_analytics(towards_analysis)
        print(f'Category: {category} | Total nav logs: {len(analytics["nav_logs_total"].keys())}')
        domains = list(analytics['nav_logs_total'].keys()) 
        param_population = check_pii_leakage_with_URL_leakage(domains)
        
        per_category_url_n_params[category] = {
            'total' : len(analytics["nav_logs_total"].keys()),
            'param_distr' : param_population
        }
        # print(analytics['nav_logs_total'].keys())
        # exit()

    #     total_websites = analytics['total_websites']
    #     nav_logs_total = len(analytics['nav_logs_total'].keys())
    #     if category not in per_category_results.keys():
    #         per_category_results[category] = {
    #             'total_websites': total_websites,
    #             'nav_logs_total': nav_logs_total
    #         }
        reset_globals()
    #     print('================================================================================================================')

    # print(per_category_results)
    # plot_per_cat(per_category_results)


    print(per_category_url_n_params)
    create_pii_heatmap(per_category_url_n_params, None)
    plt.show()