import os
import re
import sys
import json
import time
import requests
import threading
import logging
import aiohttp
import asyncio
import socket
import warnings
import random

from bs4 import BeautifulSoup
from bs4 import Tag

from urllib.parse import urljoin,urlparse
from pathlib import Path
from functools import partial


from urllib3.exceptions import InsecureRequestWarning
from requests.exceptions import RequestException




from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from multiprocessing import Process, Queue
import concurrent.futures

from concurrent.futures import ThreadPoolExecutor, as_completed
from concurrent.futures import ProcessPoolExecutor  
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, asdict


warnings.filterwarnings('ignore')
requests.packages.urllib3.disable_warnings()
logging.getLogger().setLevel(logging.CRITICAL)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

pattern_init = r'fbq\(\s*["\']init["\']\s*,\s*["\'](\d+)["\'](?:\s*,\s*[^)]*)?\s*\)'
pattern_track = r'fbq\(\s*["\']track["\']\s*,\s*["\'][^"\']*["\'](?:\s*,\s*[^;]*)?\s*\);'
keywords = {'facebook', 'fbevents', 'fbq'}



valid_html_but_flagged = dict()
invalid_html_no_response = []
pixels_found = dict()
found_nothing = list()
second_run_stateless = list()
hanging_doms = []
dns_errors = {}
baseline_timing_dict = {}
headless_timing_dict = {}


def sanitize_for_json(obj):
    if isinstance(obj, dict):
        return {k: sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(i) for i in obj]
    elif hasattr(obj, '__dict__'):
        return sanitize_for_json(obj.__dict__)
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)


async def fetch_html_async(i, domain):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'close',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }
    
    if not domain.startswith(('http://', 'https://')):
        url = 'https://' + domain
        base_domain = domain
    else:
        url = domain
        parsed = urlparse(domain)
        base_domain = parsed.netloc
        
    if ':' in base_domain:
        base_domain = base_domain.split(':')[0]
    
    try:
        ip_info = await asyncio.to_thread(socket.gethostbyname, base_domain)
        dns_success = True
    except socket.gaierror:
        dns_success = False
        dns_errors[base_domain] = "DNS_PROBE_FINISHED_NXDOMAIN"
        print(f"{i}) DNS resolution failed for {domain}")
        return None
    
    try:
        timeout = aiohttp.ClientTimeout(total=8)
        ssl_context = False  
        
        connector = aiohttp.TCPConnector(
            ssl=ssl_context,
            force_close=True,
            enable_cleanup_closed=True
        )
        
        async with aiohttp.ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers
        ) as session:
            async with session.get(url, allow_redirects=True) as response:
                final_url = str(response.url)
                
                if response.status == 200:
                    print(f"{i}) Got HTML for {domain} -> {final_url}")
                    return await response.text()
                else:
                    print(f"{i}) Error status {response.status} for {domain} -> {final_url}")
                    return f"Error fetching HTML for {domain} -> {final_url} | status code: {response.status}"
                
    except aiohttp.ClientConnectorError as e:
        dns_errors[base_domain] = str(e)
        print(f"{i}) Connection error for {domain}: {str(e)}")
        return None
    except asyncio.TimeoutError:
        print(f"{i}) Timeout fetching {domain}")
        return None
    except aiohttp.ClientError as e:
        print(f"{i}) Client error fetching {domain}: {str(e)}")
        return f"Error - Client error fetching {domain}: {str(e)}"
    except Exception as e:
        print(f"{i}) Unexpected error fetching {domain}: {str(e)}")
        return f"Error: Unexpected error fetching {domain}: {str(e)}"

def fetch_html(i, domain):
    return asyncio.run(fetch_html_async(i, domain))



def get_domains_as_list(path=None):
    with open(path, 'r') as file:
        domains = [line.strip() for line in file if line.strip()]
        file.close()

        return domains

def extract_fb_pixel_id(text):
    pattern1 = r'fbq\((?:\\?[\'"])\s*init\s*(?:\\?[\'"])\s*,\s*(?:\\?[\'"])\s*(\d{10,16})\s*(?:\\?[\'"])'
    pattern2 = r'facebook\.com\\?/tr\?id=(\d{10,16})'
    
    pixel_ids = set()  


    matches1 = re.findall(pattern1, text)
    pixel_ids.update(matches1)
    
    matches2 = re.findall(pattern2, text)
    pixel_ids.update(matches2)
    
    return list(pixel_ids) if pixel_ids else None

def check_fb_pixel(unique_id,domain):
    base_url = f'https://connect.facebook.net/signals/config/{unique_id}?domain={domain}'
    try:
        response = requests.get(base_url, timeout=3, verify=False, allow_redirects=True)
        
        if response.status_code != 200:
            print(f'Invalid status code for {unique_id}')
            return 0
        
        pattern = rf'fbq\.registerPlugin\("{unique_id}", \{{__fbEventsPlugin: 1, plugin: function\(fbq, instance, config\) \{{ /\* empty plugin \*/instance\.configLoaded\("{unique_id}"\); \}}\}}\);?\s*$'
        
        if re.search(pattern, response.text.strip()):
            print(f"Invalid ID: {unique_id} ({domain})")
            return 0
        return 1    
    except requests.exceptions.RequestException as e:
        print(f"Error checking {unique_id}: {str(e)}")
        return 0

# =================================================================================== FACEBOOK PIXEL IMPLEMENTATION SOLE ==========================================================================
def identify_fbp_basecode(domain, html_content):
    pixels_found = []

    soup = BeautifulSoup(html_content, 'html.parser')
    script_tags = soup.find_all('script')
    for script in script_tags:
      script_content = str(script)
      if any(keyword in script_content for keyword in keywords):
        init_calls = re.findall(pattern_init, script_content)
        track_calls = re.findall(pattern_track, script_content)

        if init_calls or track_calls:
            print(f'Basecode implementation of FB Pixel found for {domain}: {str(init_calls)}/{str(track_calls)}')


            pixels_found.append({
                "domain": domain,
                "init": init_calls,
                "track": track_calls
                })

            return pixels_found
            

    return None

def identify_fbp_lightweight(domain, html_content):

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        img_tags = soup.find_all('img')
        
        pattern = r'facebook\.com/tr\?id=([^&]+)&'
        
        pixels = []
        for img in img_tags:
            src = img.get('src', '')
            if 'facebook.com/tr?' in src:
                matches = re.findall(pattern, src)  
                for pixel_id in matches:
                    pixels.append((pixel_id, str(img)))
                    print(f'Lightweight implementation of FB Pixel found for {domain}: {str(img)}')
        
        if len(pixels) > 0:
            return pixels
        else:
            return None
    except Exception as e:
        return None


def identify_facebook_pixel_core_implementation(domain,html_content):

    fbp_base_code = identify_fbp_basecode(domain,html_content)
    fbp_light_code = identify_fbp_lightweight(domain,html_content)

    if fbp_base_code or fbp_light_code:
        return {
            "base_code" : fbp_base_code,
            "lightweight" : fbp_light_code
        }
    else:
        return None
    
def identify_fbp_basecode_in_the_wild(domain, html_content):
    
    pixels_found = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = str(script)
            if 'connect.facebook.net/en_US/fbevents.js' not in script_content:
                init_calls = re.findall(pattern_init, script_content)
                track_calls = re.findall(pattern_track, script_content)

                if init_calls or track_calls:
                    print(f'Implementation of FB Pixel (found in the wild) for {domain}: {str(init_calls)}/{str(track_calls)}')
                    pixels_found.append({
                        "domain": domain,
                        "init": init_calls,
                        "track": track_calls
                    })

                    return pixels_found
    except Exception as e:
        print(e)
        return None

    return None    
# =================================================================================================================================================================================================
# =================================================================================== FB PIXEL IMPLEMENTATION IN GTM ==============================================================================
def search_in_gtm(domain,html_content):
    base_code_gtm = find_gtm_scripts(domain,html_content)    
    lightweight_gtm = find_gtm_noscripts(domain,html_content)
    per_gtm_tag = dict()
    per_gtm_tag[domain] = {
        "found_flag" : 0,
        "base_code_gtm" : dict(),
        "base_code_type" : '',
        "lightweight_gtm" : dict(),
        "light_code_type" : ''
    }

    if base_code_gtm:
        for tag in base_code_gtm:
            print(f"Analyzing: {tag}")
            type_, fbps = search_for_pixel_in_gtm(domain,tag)
            if fbps:
                per_gtm_tag[domain]['found_flag'] = 1
                per_gtm_tag[domain]['base_code_type'] = type_
                per_gtm_tag[domain]['base_code_gtm'][tag] = fbps

    if lightweight_gtm:
        for tag in lightweight_gtm:
            if base_code_gtm and tag not in base_code_gtm:
                print(f"Analyzing: {tag}")
                type_, fbps = search_for_pixel_in_gtm(domain,tag)
                if fbps:
                    per_gtm_tag[domain]['found_flag'] = 1
                    per_gtm_tag[domain]['light_code_type'] = type_
                    per_gtm_tag[domain]['lightweight_gtm'][tag] = fbps
        
    return per_gtm_tag


def find_gtm_scripts(domain, html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        script_tags = soup.find_all('script')
        
        patterns = [
            # r'\(window,document,\'script\',\'dataLayer\',\'(GTM-[A-Z0-9]+)\'\)',
            r'\(\s*window\s*,\s*document\s*,\s*[\'"]script[\'"]\s*,\s*[\'"]dataLayer[\'"]\s*,\s*[\'"]?(GTM-[A-Z0-9]+)[\'"]?\s*\)',
            r'googletagmanager\.com/gtm\.js\?id=(GTM-[A-Z0-9]+)',
            r'ga\(\'require\', \'(GTM-[A-Z0-9]+)\'\)',
            r'\'(GTM-[A-Z0-9]+)\':true',
            r'\'GTM-[A-Z0-9]+\'\s*\+\s*dl|\'(GTM-[A-Z0-9]+)\'\s*\+\s*dl'
        ]

        gtm_ids = []
        for script in script_tags:
            script_content = str(script)
            for pattern in patterns:
                matches = re.findall(pattern, script_content)
                for match in matches:
                    if isinstance(match, tuple):  
                        match = next((m for m in match if m), '')
                    if match and match not in gtm_ids:
                        gtm_ids.append(match)
                        print(f'Found GTM for {domain} : {match}')

        if len(gtm_ids) > 0:
            return gtm_ids
        else:
            return None
    except Exception as e:
        return None

def find_gtm_noscripts(domain, html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        noscript_tags = soup.find_all('noscript')
        pattern = r'https://www\.googletagmanager\.com/ns\.html\?id=(GTM-[A-Z0-9]+)'
        
        gtm_urls = []
        for noscript in noscript_tags:
            iframe = noscript.find('iframe')
            if iframe and iframe.get('src'):
                match = re.search(pattern, iframe.get('src'))
                if match:
                    gtm_urls.append(match.group(1))
                    print(f'Found GTM lightweight for {domain} : {str(match.group(1))}')
        
        if len(gtm_urls) > 0:
            return gtm_urls
        else:
            return None
    except Exception as e:
        return None


def get_fbpid_from_vtp(text,domain):
    pattern = r'"vtp_pixelId"\s*:\s*"(\d+)"'
    
    matches = re.findall(pattern, text)   
    unique_ids = list(set(matches))
    final_ids = []
    for unique_id in unique_ids:
        ret_val = check_fb_pixel(unique_id,domain)
        if ret_val != 0:
            final_ids.append(unique_id)

    if len(final_ids) > 0:
        return final_ids
    else:
        return None

def extract_tags_array(content):
    try:
        start_marker = '"tags":['
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("No macros array found")
            return None
        
        start_idx += len(start_marker) - 1  
        bracket_count = 0
        in_string = False
        escape_char = False
        
        for i in range(start_idx, len(content)):
            char = content[i]
            
            if char == '"' and not escape_char:
                in_string = not in_string
            
            if char == '\\' and not escape_char:
                escape_char = True
                continue
            escape_char = False
            
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        tags_str = content[start_idx:i+1]
                        try:
                            return tags_str
                        except json.JSONDecodeError as e:
                            print(f"Error parsing extracted array: {str(e)}")
                            return None

    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return None

def extract_macros_array(content):
    try:
        start_marker = '"macros":['
        start_idx = content.find(start_marker)
        if start_idx == -1:
            print("No macros array found")
            return None
        
        start_idx += len(start_marker) - 1  
        bracket_count = 0
        in_string = False
        escape_char = False
        
        for i in range(start_idx, len(content)):
            char = content[i]
            
            if char == '"' and not escape_char:
                in_string = not in_string
            
            if char == '\\' and not escape_char:
                escape_char = True
                continue
            escape_char = False
            
            if not in_string:
                if char == '[':
                    bracket_count += 1
                elif char == ']':
                    bracket_count -= 1
                    if bracket_count == 0:
                        macros_str = content[start_idx:i+1]
                        try:
                            return json.loads(macros_str)
                        except json.JSONDecodeError as e:
                            print(f"Error parsing extracted array: {str(e)}")
                            return None

    except Exception as e:
        print(f"Error processing text: {str(e)}")
        return None

def get_facebook_vtp_functions(tags_array):
    facebook_related_funcs = []

    for tag in json.loads(tags_array):
        if "once_per_load" in tag.keys():
            if tag['once_per_load'] == True:
                if 'vtp_html' in tag.keys():
                    vtp_html = str(tag['vtp_html'])
                    if 'https://connect.facebook.net/en_US/fbevents.js' in vtp_html and 'fbq("track","PageView");' in vtp_html:
                        facebook_related_funcs.append(str(vtp_html))
                        break
        else:
            pass


    return facebook_related_funcs


def parse_domain_list(domain_list):
    mappings = domain_list[1:]
    
    result = {}
    for item in mappings:
        if len(item) == 5 and item[0] == 'map' and item[1] == 'key' and item[3] == 'value':
            domain = item[2]
            clean_domain = (domain.replace('^', '').replace('$', '').replace('(?:www\\.)?', '').replace('\\', '').replace('m\\.', '').replace('mlite\\.', ''))
            result[clean_domain] = item[4]
    
    if len(result.keys()) > 0:
        return result
    else:
        return None

def find_fbq_macro_value(content):
    macros = extract_macros_array(content)
    if not macros:
        return None
    
    try:
        tags_array = extract_tags_array(content)
        fb_vtp_funcs = get_facebook_vtp_functions(tags_array)
        fbq_macros = {}
        for vtp_func in fb_vtp_funcs:
            init_pattern = r'fbq\(["\']init["\'],\s*["\']["\']?,\s*\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'

            init_pattern2 = r'fbq\(["\']init["\'],.*?\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'


            macro_indices = re.findall(init_pattern, vtp_func)
            
            
            if macro_indices:
                for index in list(set(macro_indices)):
                    index = int(index)
                    if index < len(macros):
                        fbq_macros[index] = macros[index]
            else:
                macro_indices = re.findall(init_pattern2, vtp_func)
                for index in list(set(macro_indices)):
                    index = int(index)
                    if index < len(macros):
                        fbq_macros[index] = macros[index]

        pixel_ids = []
        mappings_domain_to_fbID = {}
        if fbq_macros:
            for macro in fbq_macros.keys():
                as_array = fbq_macros[macro]
                if 'function' in as_array.keys():
                    if as_array['function'] == "__c":
                        if 'vtp_value' in as_array.keys():
                            pixel_ids.append(as_array['vtp_value'])
                    
                    if as_array['function'] == "__smm":
                        if 'vtp_setDefaultValue' in as_array.keys():
                            if as_array['vtp_setDefaultValue'] == True:
                                pixel_ids.append(as_array['vtp_defaultValue'])
                            else:
                                mappings_domain_to_fbID = parse_domain_list(as_array['vtp_map'])
                                
        if len(pixel_ids) > 0:
            return list(set(pixel_ids))
        else:
            if len(mappings_domain_to_fbID.keys()) > 0:
                return mappings_domain_to_fbID
            else:
                return None

    except Exception as e:
        print(f"Error processing: {str(e)}")
        return None

def validate_html_script(tags):
    fb_ids = []
    if len(tags) == 1:
        fb_ids = extract_fb_pixel_id(tags[0]['vtp_html'])
    else:
        for tag in tags:
            if 'vtp_supportDocumentWrite' in tag:
                    if tag['vtp_supportDocumentWrite'] == True:
                        temp_ids = extract_fb_pixel_id(tag['vtp_html'])
                        for temp_id in temp_ids:
                            fb_ids.append(temp_id)

    if len(fb_ids) > 0:
        return list(set(fb_ids))
    else:
        return None

def search_in_tags(tag_html,content):

    init_pattern = r'fbq\(["\']init["\'],\s*["\']["\']?,\s*\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'
    init_pattern2 = r'fbq\(["\']init["\'],.*?\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'

    baseline_ids = extract_fb_pixel_id(str(tag_html))
    if baseline_ids:
        print(baseline_ids)
    else:
        tag_html = str(tag_html)

        macros = extract_macros_array(content)
        init_pattern = r'fbq\(["\']init["\'],\s*["\']["\']?,\s*\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'

        init_pattern2 = r'fbq\(["\']init["\'],.*?\[\s*["\']escape["\'],\s*\[\s*["\']macro["\'],\s*(\d+)\s*\]'

        macro_indices = re.findall(init_pattern, tag_html)
        fbq_macros = dict()


        if macro_indices:
            for index in list(set(macro_indices)):
                index = int(index)
                if index < len(macros):
                    fbq_macros[index] = macros[index]
        else:
            macro_indices = re.findall(init_pattern2, tag_html)
            for index in list(set(macro_indices)):
                index = int(index)
                if index < len(macros):
                    fbq_macros[index] = macros[index]
        
        pixel_ids = []
        mappings_domain_to_fbID = []
        if fbq_macros:
            for macro in fbq_macros.keys():
                as_array = fbq_macros[macro]      
                if 'vtp_setDefaultValue' in as_array.keys():                  
                    if as_array['vtp_setDefaultValue'] == True:
                        pixel_ids.append(as_array['vtp_defaultValue'])
                    else:
                        mappings_domain_to_fbID = parse_domain_list(as_array['vtp_map'])


        if mappings_domain_to_fbID:
            return mappings_domain_to_fbID
        elif pixel_ids:
            return pixel_ids
        else:
            return None

def find_pixel_ids(content, tag):
   try:           
        pattern = r'\b\d{15,16}\b'
        pixel_ids = re.findall(pattern, content)
        
        if pixel_ids:
            print(f"Found Pixel IDs in {tag} (generic heuristic)")
            return list(set(pixel_ids))
        else:
            print(f"No pixel IDs found in {tag} (generic heuristic)")
            return None
   except Exception as e:
       print(f"Error reading file: {str(e)}")
       return None

def search_for_pixel_in_gtm(domain,tag):

    try:
        gtm_url = 'https://www.googletagmanager.com/gtm.js?id='+tag
        response = requests.get(gtm_url, timeout=5, verify=False, allow_redirects=True)

        if response.status_code == 200:
            content = str(response.text)
            fbp = extract_fb_pixel_id(content)
            if fbp:
                print(f"GTM: {tag} has FB Pixel with ID: {fbp}")
                return "basic", fbp
            else:
                print('Searching for VTP')
                fbp_ids_vtp = get_fbpid_from_vtp(content,domain)
                if fbp_ids_vtp:
                    if len(fbp_ids_vtp) > 0:
                        return "vtp", fbp_ids_vtp
                else:
                    print('* No VTP values found searching for macros')
                    fbp_ids_macros = find_fbq_macro_value(content)
                    if isinstance(fbp_ids_macros, dict):
                        return "mappings", fbp_ids_macros
                    elif isinstance(fbp_ids_macros, list):
                        return "simple_list", fbp_ids_macros
                    else:

                        print('* No macros values found searching for generic')
                        pixel_ids = find_pixel_ids(content, tag)
                        if pixel_ids:
                            return "potential", list(set(pixel_ids))
        else:
            print('????????????????????? for {}')
    except Exception as e:
        return None, None                    

    return None, None

# =================================================================================================================================================================================================
def count_html_lines(html_content, pretty=True):
    raw_lines = len(html_content.splitlines())
    
    if pretty:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            formatted_content = soup.prettify()
            formatted_lines = len(formatted_content.splitlines())
        except Exception as e:
            print(f"Error formatting HTML: {e}")
            return raw_lines, raw_lines, html_content
            
        return raw_lines, formatted_lines, formatted_content
    
    return raw_lines, raw_lines, html_content

def check_meta_refresh(html_content, domain):
    base_url = ''
    if not domain.startswith(('http://', 'https://')):
        base_url = 'https://' + domain

    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        meta = soup.find('meta', attrs={'http-equiv': re.compile('^refresh$', re.I)})
        
        if not meta:
            print("No meta refresh found")
            return False, None
            
        content = meta.get('content', '')
        if not content:
            print("Meta refresh found but no content attribute")
            return False, None
            
        match = re.search(r'url\s*=\s*(.+)', content, re.I)
        
        if not match:
            print(f"No URL found in content: {content}")
            return False, None
            
        url = match.group(1).strip()
        
        url = url.strip('"\'')
        
        if not url.startswith(('http://', 'https://')):
            if url.startswith('/'):
                url = base_url+url
            else:
                url = base_url+'/'+url

            
        print(f"Found meta refresh redirect to: {url}")
        return True, url
        
    except Exception as e:
        print(f"Error parsing HTML: {e}")
        return False, None




# def get_fbq_state(domain):
#     chrome_options = Options()
#     chrome_options.add_argument("--headless=new")
#     chrome_options.add_argument("--no-sandbox")
#     chrome_options.add_argument("--disable-dev-shm-usage")
#     chrome_options.add_argument("--disable-gpu")
#     chrome_options.add_argument('--enable-javascript')
#     chrome_options.add_argument('--window-size=1920,1080')
#     chrome_options.add_argument('--dns-prefetch-disable')
#     chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

#     # chrome_options.page_load_strategy = 'eager'

#     driver = webdriver.Chrome(options=chrome_options)
#     driver.set_page_load_timeout(60)

#     try:
#         if not domain.startswith(('http://', 'https://')):
#             domain = 'https://' + domain

#         driver.get(domain)

#         WebDriverWait(driver, 20).until(
#             EC.presence_of_element_located((By.TAG_NAME, 'body'))
#         )

#         start_time = time.time()
#         fbq_state = None

#         while time.time() - start_time < 10:
#             try:
#                 fbq_state = driver.execute_script("""
#                     if (typeof fbq !== 'undefined' && typeof fbq.getState === 'function') {
#                         try {
#                             const state = fbq.getState();
#                             if (state && state.pixels && state.pixels.length > 0) {
#                                 return JSON.stringify(state);
#                             }
#                         } catch (e) {}
#                     }
#                     return null;
#                 """)
                
#                 if fbq_state:
#                     break  

#             except Exception:
#                 pass

#             time.sleep(0.5)

#         if fbq_state:
#             parsed_state = json.loads(fbq_state)
#             print(f"\nFacebook Pixel State for {domain}:")
#             print(json.dumps(parsed_state, indent=2))
#             driver.quit()
#             return 'FBP', parsed_state

#         try:
#             gtm_ids = driver.execute_script("""
#                 return Array.from(new Set([...document.documentElement.innerHTML.match(/GTM-[A-Z0-9]+/g) || []]));
#             """)
#         except Exception:
#             gtm_ids = []

#         if gtm_ids:
#             print(f'Found GTM in headless: {str(gtm_ids)}')
#             implementations = []
#             patterns = get_fb_patterns()

#             for gtm_id in gtm_ids:
#                 print(f'Analyzing : {gtm_id}')
#                 implementation_type, pixel_ids = search_for_pixel_in_gtm(domain,gtm_id)
#                 if pixel_ids:
#                     print(f'Found Pixel for {domain} in GTM {gtm_id}')
#                     for pixel_id in pixel_ids:
#                         implementations.append(pixel_id)
#                 else:
#                     print(f'No Pixels found in {gtm_id}')
#             driver.quit()
#             if implementations:
#                 return 'GTM', implementations 
            

#         try:
#             print(f"\n\nHTML for {domain} (no pixel found):")
#             html_content = driver.page_source
#             if "fbq(" in html_content or "facebook-jssdk" in html_content or "connect.facebook.net" in html_content:
#                 print("\nFacebook Pixel related code detected in HTML but not accessible via fbq.getState()")                
#                 pixel_id_pattern = r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d+)['\"]\s*\)"
#                 import re
#                 pixel_matches = re.findall(pixel_id_pattern, html_content)
#                 if pixel_matches:
#                     print(f"Potential Facebook Pixel IDs found in HTML: {pixel_matches}")
            
#         except Exception as e:
#             print(f"Error printing HTML: {str(e)}")
        
#         driver.quit()
#         driver.quit()
#         return None, None

#     except Exception as e:
#         print(f"Error getting fbq state for {domain}: {str(e)}")
#         try:
#             driver.quit()
#         except:
#             pass
#         return None, None

def get_fbq_state(domain):
    driver = None
    try:
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument('--enable-javascript')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--dns-prefetch-disable')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins')
        chrome_options.add_argument('--disable-images')  
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(60)

        if not domain.startswith(('http://', 'https://')):
            domain = 'https://' + domain

        print(f"Loading {domain}...")
        driver.get(domain)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

        print("Page loaded, checking for Facebook Pixel...")
        
        start_time = time.time()
        fbq_state = None

        while time.time() - start_time < 10:
            try:
                fbq_state = driver.execute_script("""
                    if (typeof fbq !== 'undefined' && typeof fbq.getState === 'function') {
                        try {
                            const state = fbq.getState();
                            if (state && state.pixels && state.pixels.length > 0) {
                                return JSON.stringify(state);
                            }
                        } catch (e) {
                            console.log('Error getting fbq state:', e);
                        }
                    }
                    return null;
                """)
                
                if fbq_state:
                    break  

            except Exception as e:
                print(f"Error executing script: {str(e)}")
                break

            time.sleep(0.5)

        if fbq_state:
            parsed_state = json.loads(fbq_state)
            print(f"\nFacebook Pixel State for {domain}:")
            print(json.dumps(parsed_state, indent=2))
            return 'FBP', parsed_state

        try:
            print("Checking for GTM...")
            gtm_ids = driver.execute_script("""
                return Array.from(new Set([...document.documentElement.innerHTML.match(/GTM-[A-Z0-9]+/g) || []]));
            """)
        except Exception as e:
            print(f"Error checking for GTM: {str(e)}")
            gtm_ids = []

        if gtm_ids:
            print(f'Found GTM in headless: {str(gtm_ids)}')
            implementations = []
            
            for gtm_id in gtm_ids:
                print(f'Analyzing : {gtm_id}')
                try:
                    implementation_type, pixel_ids = search_for_pixel_in_gtm(domain, gtm_id)
                    if pixel_ids:
                        print(f'Found Pixel for {domain} in GTM {gtm_id}')
                        for pixel_id in pixel_ids:
                            implementations.append(pixel_id)
                    else:
                        print(f'No Pixels found in {gtm_id}')
                except Exception as e:
                    print(f"Error analyzing GTM {gtm_id}: {str(e)}")
            
            if implementations:
                return 'GTM', implementations 

        try:
            print(f"Checking HTML source for Facebook Pixel code...")
            html_content = driver.page_source
            
            if "fbq(" in html_content or "facebook-jssdk" in html_content or "connect.facebook.net" in html_content:
                pixel_patterns = [
                    r"fbq\(\s*['\"]init['\"]\s*,\s*['\"](\d+)['\"]\s*\)",
                    r"facebook\.com/tr\?id=(\d+)",
                    r"pixelId['\"]?\s*[:=]\s*['\"](\d+)['\"]",
                ]
                
                all_pixel_ids = []
                for pattern in pixel_patterns:
                    matches = re.findall(pattern, html_content)
                    all_pixel_ids.extend(matches)
                
                unique_pixel_ids = list(set(all_pixel_ids))
                if unique_pixel_ids:
                    return 'HTML', unique_pixel_ids
                else:
                    print("Facebook Pixel code found but no pixel IDs extracted")
            else:
                print("No Facebook Pixel code detected")
                
        except Exception as e:
            print(f"Error checking HTML: {str(e)}")
        
        return None, None

    except Exception as e:
        print(f"Error getting fbq state for {domain}: {str(e)}")
        return None, None
        
    finally:
        if driver:
            try:
                driver.current_url
                driver.quit()
                print("Driver closed successfully")
            except Exception as e:
                print(f"Driver was already closed or crashed: {str(e)}")
                try:
                    driver.service.stop()
                except:
                    pass


# ========================================================================== CHECK FOR FACEBOOK PIXEL ON OTHER THIRD PARTIES =====================================================================
@dataclass
class FacebookPixelImplementation:
    pixel_id: str
    implementation_type: str
    script_url: Optional[str]
    script_content: str
    context: str
    custom_config: Dict

def get_fb_patterns():
    patterns = {
        'pixel_ids': [
            r'fbq\s*\(\s*[\'"]init[\'"]\s*,\s*[\'"](\d{15,16})[\'"]',
            r'https://connect\.facebook\.net/.+/fbevents\.js#xfbml=1&version=.*&pixelid=(\d{15,16})',
            r'fb_pixel_id\s*[:=]\s*[\'"](\d{15,16})[\'"]',
            r'pixel_id\s*[:=]\s*[\'"](\d{15,16})[\'"]',
            r'facebook_pixel_id\s*[:=]\s*[\'"](\d{15,16})[\'"]',
            r'facebook\.com/tr\?id=(\d{15,16})',
            r'pixel:\s*{[^}]*id:\s*[\'"]?(\d{15,16})[\'"]?',
        ],
        'base_code': [
            r'!function\(f,b,e,v,n,t,s\).*fbevents\.js.*\(window,\s*document,\s*[\'"]script[\'"]\s*,\s*[\'"]https://connect\.facebook\.net/en_US/fbevents\.js[\'"]',
            r'fbq\s*\(\s*[\'"]init[\'"]',
            r'window\.fbq\s*=\s*function\(\)',
        ],
        'lightweight': [
            r'<img\s+height="1"\s+width="1"\s+.*?facebook\.com/tr\?id=\d{15,16}',
            r'<noscript>.*?facebook\.com/tr\?id=\d{15,16}.*?</noscript>',
            r'https://connect\.facebook\.net/.+/fbevents\.js#.*?pixelid=\d{15,16}',
        ],
        'custom_events': [
            r'fbq\s*\(\s*[\'"]track[\'"]',
            r'fbq\s*\(\s*[\'"]trackCustom[\'"]',
        ]
    }
    
    return {
        category: [re.compile(pattern, re.IGNORECASE | re.MULTILINE) 
                  for pattern in patterns]
        for category, patterns in patterns.items()
    }

def extract_pixel_id(content, patterns):
    """Extract Facebook Pixel ID from content."""
    for pattern in patterns['pixel_ids']:
        match = re.search(pattern, content)
        if match and match.group(1):
            pixel_id = match.group(1)
            if re.match(r'^\d{15,16}$', pixel_id):
                return pixel_id
    return None

def analyze_script_content(content, url, patterns):
    """Analyze script content for Facebook Pixel implementations."""
    pixel_id = extract_pixel_id(content, patterns)
    if not pixel_id:
        return None

    implementation_type = 'standard'
    if any(pattern.search(content) for pattern in patterns['lightweight']):
        implementation_type = 'lightweight'
    elif url and 'facebook' not in url.lower():
        implementation_type = 'third-party'

    custom_events = []
    for pattern in patterns['custom_events']:
        matches = pattern.finditer(content)
        for match in matches:
            start = max(0, match.start() - 50)
            end = min(len(content), match.end() + 150)
            custom_events.append(content[start:end])
    
    custom_config = {'custom_events': custom_events} if custom_events else {}

    pixel_match = re.search(pixel_id, content)
    context = ""
    if pixel_match:
        start = max(0, pixel_match.start() - 100)
        end = min(len(content), pixel_match.end() + 100)
        context = content[start:end]

    return FacebookPixelImplementation(
        pixel_id=pixel_id,
        implementation_type=implementation_type,
        script_url=url,
        script_content=content[:1000] if len(content) > 1000 else content,
        context=context,
        custom_config=custom_config
    )

def fetch_and_analyze_script(script_url, patterns):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1'
    }

    try:
        response = requests.get(script_url, headers=headers, timeout=10)
        response.raise_for_status()
        return analyze_script_content(response.text, script_url, patterns)
    except RequestException as e:
        return None

def analyze_single_script(script, base_url, patterns, processed_urls):
    try:
        if hasattr(script, 'src') and script.get('src'):
            script_url = urljoin(base_url, script.get('src'))
            if script_url not in processed_urls:
                processed_urls.add(script_url)
                return fetch_and_analyze_script(script_url, patterns)
        elif script.string:
            return analyze_script_content(script.string, base_url, patterns)
        elif isinstance(script, Tag):  
            return analyze_script_content(str(script), base_url, patterns)
    except Exception as e:
        logging.error(f"Error analyzing script: {e}")
    return None



def find_fbp_on_other_thirdparties(domain, content):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    base_url = domain if domain.startswith(('http://', 'https://')) else 'https://' + domain
    logger.info(f"Analyzing {base_url}")

    try:
        patterns = get_fb_patterns()
        implementations = []
        processed_urls = set()
        soup = BeautifulSoup(content, 'html.parser')

        scripts_to_analyze = []
        scripts_to_analyze.extend(soup.find_all('noscript'))
        scripts_to_analyze.extend(soup.find_all('script', src=False))
        scripts_to_analyze.extend(soup.find_all('script', src=True))

        analyze_script = partial(analyze_single_script, 
                               base_url=base_url, 
                               patterns=patterns, 
                               processed_urls=processed_urls)

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_script = {
                executor.submit(analyze_script, script): script 
                for script in scripts_to_analyze
            }

            for future in as_completed(future_to_script):
                try:
                    implementation = future.result()
                    if implementation:
                        implementations.append(implementation)
                except Exception as e:
                    logger.error(f"Error processing script: {e}")

        if implementations:
            return {
                'url': base_url,
                'implementations': [asdict(impl) for impl in implementations],
                'total_implementations': len(implementations),
                'unique_pixels': len(set(impl.pixel_id for impl in implementations))
            }
        
        return None

    except Exception as e:
        logger.error(f"Error analyzing {base_url}: {str(e)}")
        return None

# ================================================================================================================================================================================================
# ================================================================================= CHECK FOR FACEBOOK SOCIAL MEDIA PRESENCE =====================================================================
def find_facebook_page(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    
    indicators = [
        {'class_': re.compile(r'(?i)(facebook|fb|social|follow)')},
        {'id': re.compile(r'(?i)(facebook|fb|social|follow)')},
        {'string': re.compile(r'(?i)(facebook|follow us|social)')}
    ]
    
    url_patterns = [
        r'facebook\.com/(?!sharer|share|login|photo|events|groups|gaming|watch|marketplace)[\w\.-]+/?$',
        r'fb\.me/[\w\.-]+/?$'
    ]
    
    potential_links = set()
    
    for indicator in indicators:
        anchors = soup.find_all('a', **indicator)
        for anchor in anchors:
            href = anchor.get('href')
            if href:
                if any(re.search(pattern, href.lower()) for pattern in url_patterns):
                    potential_links.add(href)
    
    
    icon_elements = soup.find_all(['i', 'span', 'div'], class_=re.compile(r'(?i)(fa-facebook|facebook-icon|icon-fb)'))
    for icon in icon_elements:
        parent_anchor = icon.find_parent('a')
        if parent_anchor and parent_anchor.get('href'):
            href = parent_anchor.get('href')
            if any(re.search(pattern, href.lower()) for pattern in url_patterns):
                potential_links.add(href)
    
    social_containers = soup.find_all(['div', 'section', 'footer'], class_=re.compile(r'(?i)(social|footer)'))
    for container in social_containers:
        anchors = container.find_all('a')
        for anchor in anchors:
            href = anchor.get('href')
            if href and any(re.search(pattern, href.lower()) for pattern in url_patterns):
                potential_links.add(href)
    
    return list(potential_links)

def check_website_facebook(content):
    try:
        facebook_pages = find_facebook_page(content)
        return facebook_pages
    except Exception as e:
        print(f"Error: {e}")
        return []
    
# ================================================================================================================================================================================================
# ================================================================================================================================================================================================
#                                                                                                    CORE
# ================================================================================================================================================================================================

def find_FBP(domains_list_path=None,domain_single=None,flag=0):

    global valid_html_but_flagged, invalid_html_no_response, pixels_found, found_nothing, baseline_timing_dict, hanging_doms
    
    domains = []
    if flag == 0:
        domains = get_domains_as_list(domains_list_path)
    else:
        domains = [domain_single]
    

    found_so_far = 0
    for i in range(len(domains)):
        start_time = time.time()
        print('================================================================================================================================')
        print(f"{i}) Processing domain: {domains[i]}    | Found in : {found_so_far}/{len(domains)}")
        try:
            content = fetch_html(i,domains[i])
            if content:
                if content.startswith('Error'):
                    invalid_html_no_response.append(domains[i])
                else:
                    flag, url = check_meta_refresh(content,domains[i])
                    if flag == True:
                        content = fetch_html(i,url)
                    
                    if content:
                        raw_lines, formatted_lines, formatted_content = count_html_lines(content)
                        if (raw_lines < 30) and (formatted_lines < 30):
                            valid_html_but_flagged[domains[i]] = formatted_content
                        else:
                            print(f'Fetched {domains[i]}')
                            fbpixel_core = identify_facebook_pixel_core_implementation(domains[i],content)
                            if fbpixel_core:
                                pixels_found[domains[i]] = {
                                    'PIXEL_CORE' : fbpixel_core,
                                }
                                found_so_far += 1
                            else:
                                fbpixel_in_the_wild = identify_fbp_basecode_in_the_wild(domains[i],content)
                                if fbpixel_in_the_wild:
                                    pixels_found[domains[i]] = {
                                        'PIXEL_WILD' : fbpixel_core,
                                    }
                                    found_so_far += 1
                                else:
                                    pixel_in_gtm = search_in_gtm(domains[i],content)
                                    if pixel_in_gtm[domains[i]]['found_flag'] == 1:
                                        pixels_found[domains[i]] = {
                                            'PIXEL_GTM' : pixel_in_gtm,
                                        }
                                        found_so_far += 1
                                    else:
                                        pixels_in_other_tp = find_fbp_on_other_thirdparties(domains[i],content)
                                        if pixels_in_other_tp:
                                            print('Found Pixel in other third party scripts')
                                            pixels_found[domains[i]] = {
                                                'PIXEL_IN_OTHER_TP' : pixels_in_other_tp
                                            }
                                            found_so_far += 1
                                        else:
                                            if len(check_website_facebook(content)) > 0:
                                                second_run_stateless.append(domains[i])
                                            else:
                                                found_nothing.append(domains[i])
                        
                        baseline_timing_dict[domains[i]] = f"{time.time() - start_time:.2f}"
                    else:
                        print(f'Redirect hanged: {domains[i]}')
                        hanging_doms.append(domains[i])              
            else:
                print(f'Totaly hanged {domains[i]}')
                hanging_doms.append(domains[i])
            print('================================================================================================================================')
        except Exception as e:
            print('================================================================================================================================')
            continue        
    return domains



def process_domain(domain):
    try:
        start_time = time.time()
        state_type, state = get_fbq_state(domain)
        print('====================')
        print(state_type)
        print(state)
        print('====================')

        domain_pixel_ids = []
        
        if state: 
            if 'pixels' in state:
                for pixel in state['pixels']:
                    domain_pixel_ids.append(pixel['id'])
            else:
                if len(state) > 0:
                    for pixel_id in state:
                        domain_pixel_ids.append(pixel_id)
        
        processing_time = f"{time.time() - start_time:.2f}"
        logger.info(f"Processed {domain} in {processing_time} seconds")
        
        return domain, domain_pixel_ids,processing_time, state_type  
    
    except Exception as e:
        logger.error(f"Error processing {domain}: {e}")
        return domain, [], "0.00", None
    


def find_pixel_ids_state(domains, max_workers=3, overall_timeout=30):
    pixels_found = {}
    timing_dict = {} 
    timeout_count = 0
    error_count = 0
    empty_count = 0
    
    logger.info(f"Starting processing of {len(domains)} domains")

    if len(domains) < 3:
        max_workers = len(domains)

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_domain, domain): domain for domain in domains}
        
        try:
            for future in as_completed(futures):
                domain = futures[future]
                try:
                    domain, pixel_ids, process_time, state_type = future.result() 
                    timing_dict[domain] = process_time  
                    if pixel_ids:
                        serializable_ids = []
                        for pid in pixel_ids:
                            try:
                                json.dumps(pid)
                                serializable_ids.append(pid)
                            except (TypeError, OverflowError):
                                serializable_ids.append(str(pid))

                        pixels_found[domain] = {
                            'pixel_ids': serializable_ids,
                            'state_type': str(state_type)
                        }
                    else:
                        empty_count += 1
                        logger.info(f"No pixels found for domain: {domain}")
                except concurrent.futures.TimeoutError:
                    timeout_count += 1
                    logger.warning(f"Timeout for domain: {domain}")
                except Exception as exc:
                    error_count += 1
                    logger.error(f'{domain} generated an exception: {exc}')
        
        except concurrent.futures.TimeoutError:
            remaining = sum(1 for f in futures if not f.done())
            logger.error(f"Overall process timed out with {remaining} domains remaining")
        
        finally:
            cancelled = 0
            for future in futures:
                if not future.done():
                    future.cancel()
                    cancelled += 1
            
            logger.info(f"""
                Processing complete:
                - Successful with pixels: {len(pixels_found)}
                - No pixels found: {empty_count}
                - Individual timeouts: {timeout_count}
                - Errors: {error_count}
                - Cancelled: {cancelled}
                Total domains: {len(domains)}
                Average processing time: {sum(float(t) for t in timing_dict.values())/len(timing_dict):.2f} seconds
            """)
            
            executor.shutdown(wait=True)
    
    return pixels_found, timing_dict 


# ================================================================================================================================================================================================
# ================================================================================================================================================================================================


def main():

    help_panel = """Example execution: python3 get_statically_all_pixel_instances.py -[f/d] -[path/domain]
    where:
    \t  -f -path  : specify a text file (of domains) usage and providing the corresponding path
    \t  -d -domain: specify a single domain usage and providing the domain 
    """
    path = ''
    domain = ''

    if len(sys.argv) != 3:
        print(help_panel)
        exit()
    else:
        if sys.argv[1] == '-f':
            path = sys.argv[2]
        elif sys.argv[1] == '-d':
            domain = sys.argv[2]
        else:
            print(help_panel)
            exit()

    global found_nothing, second_run_stateless, valid_html_but_flagged, invalid_html_no_response, pixels_found
    global headless_timing_dict, baseline_timing_dict
    start_time = time.time()
    total_doms = []
    
    if len(domain) > 1:
        if domain.startswith('www.'):
            pass
        else:
            domain = 'www.'+domain
        
        total_doms = find_FBP(None,domain,1)
    else:
        total_doms = find_FBP(path,None,0)
    
    print('--------------------------------------------------------------------------------------------------------------')
    print('                                 PERFORMING STATE SEARCH                                                      ')
    print('--------------------------------------------------------------------------------------------------------------')
    max_workers = 6  
    overall_timeout = 300  
    
    try:
        total_headless = []
        for domain in total_doms:
            if domain not in pixels_found.keys(): 
                total_headless.append(domain)

        total_headless = list(set(total_headless))
        

        state_fbq, timings = find_pixel_ids_state(total_headless, max_workers=max_workers, overall_timeout=overall_timeout)
        headless_timing_dict = timings
        logger.info(f"State search completed. Found pixel IDs for {len(state_fbq)} domains")
    except Exception as e:
        logger.error(f"Error during state search: {e}")
        state_fbq = {}  



    print(f"Found pixel IDs for {len(state_fbq.keys())} domains")

    print('--------------------------------------------------------------------------------------------------------------')
    print(f'Total execution time: {time.time() - start_time:.2f} seconds')
    
    with open('./crawler_output/baseline_timings.json', 'w') as f:
        json.dump(baseline_timing_dict, f, indent=4)
        f.close()

    with open('./crawler_output/headless_timings.json', 'w') as f:
        json.dump(headless_timing_dict, f, indent=4)
        f.close()

    with open('./crawler_output/flagged_erroneous_html_responses.json', 'w') as f:
        json.dump(valid_html_but_flagged, f, indent=4)
        f.close()

    with open('./crawler_output/pixels_found.json', 'w') as f:
        json.dump(pixels_found, f, indent=4)
        f.close()

    with open('./crawler_output/invalid_html_no_response.txt','w') as f:
        for domain in invalid_html_no_response:
            f.write(domain+'\n')
        f.close()


    with open('./crawler_output/found_nothing.txt','w') as f:
        for domain in found_nothing:
            f.write(domain+'\n')
        f.close()

    with open('./crawler_output/total_hanged.txt','w') as f:
        for domain in hanging_doms:
            f.write(domain+'\n')
        f.close()

    with open('./crawler_output/state_fbq.json', 'w') as f:
        json.dump(state_fbq, f, indent=4)
        f.close()


if __name__ == "__main__":
    main()
