# -*- coding: utf-8 -*-
"""
Udemy Scraper v40 - THE PERFECT CODE

CÁC TÍNH NĂNG HOÀN THIỆN:
1. LOGIC GIÁ CHUẨN (v35): Max/Min Strategy + Regex Cleaning + HTML Fallback.
2. LOGIC DỪNG CHUẨN (v24): Dừng khi 2 trang liên tiếp < 16 link.
3. LOGIC TEST CHUẨN (v39): Test từ trang bất kỳ, chỉ chạy 2 trang.
4. LOGIC LOGIN CHUẨN (v32): Cookie Injection từ profile login thủ công.
5. MAIN LOGIC LINH HOẠT: Chạy theo Category lẻ hoặc Group, cho cả Dashboard và Tracker.
"""

import os
import sys
import io
import time
import json
import random
import argparse
import hashlib
import shutil
import datetime
import gc
import re
from typing import List, Dict, Optional, Tuple
import requests as standard_requests 
# --- CÀI ĐẶT ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(SCRIPT_DIR, "log") 
MASTER_PROFILE_DIR = os.path.join(SCRIPT_DIR, "udemy_profile") 

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from bs4 import BeautifulSoup

# --- MODULES ---
try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
except ImportError:
    print("LỖI: Chưa cài 'playwright'.")
    sys.exit(1)

try:
    from curl_cffi import requests
    Session = requests.Session
except ImportError:
    print("LỖI: Chưa cài 'curl_cffi'.")
    sys.exit(1)

from dotenv import load_dotenv
import boto3
from botocore.client import Config

# =========================
# SETTINGS
# =========================
PAGELOAD_TIMEOUT = 240  
SCROLL_STEPS = 15      
PAGES_PER_BATCH = 40   
MAX_CONSECUTIVE_LOW_DATA = 2 
ELEMENT_TIMEOUT = 10000 

IMPERSONATE_PROFILES = ["chrome120", "chrome110", "chrome107"]

# =========================
# HELPER FUNCTIONS
# =========================

def get_proxies() -> Optional[Dict]:
    api_url = os.getenv("PROXY_API_URL")
    if not api_url: return None

    # Hỗ trợ định dạng chuỗi proxy trực tiếp (VD: http://user:pass@host:port)
    if "@" in api_url and (api_url.startswith("http") or api_url.startswith("socks")):
        return {"http": api_url, "https": api_url}

    # Tương thích Format kiểu cũ: host:port:user:pass
    try:
        with standard_requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10) as r: pass
        time.sleep(1)
    except: pass
    try:
        resp = requests.get(api_url, timeout=10, impersonate="chrome120")
        data = resp.json()
        proxy_str = None
        
        # Tương thích Format cũ
        if data.get("proxyhttp") or data.get("proxy"):
            proxy_str = data.get("proxyhttp") or data.get("proxy")
        # Tương thích Format VIP IP Allow mới
        elif "data" in data and "proxy_connection" in data.get("data", {}):
            conn = data["data"]["proxy_connection"]
            ip = conn.get("ip")
            port = conn.get("http_ipv4")
            if ip and port and str(port) != "-1":
                proxy_str = f"{ip}:{port}"

        if not proxy_str: return None
        
        parts = proxy_str.split(":")
        if len(parts) == 4: auth = f"{parts[2]}:{parts[3]}@{parts[0]}:{parts[1]}"
        elif len(parts) == 2: auth = f"{parts[0]}:{parts[1]}"
        else: return None
        return {"http": f"http://{auth}", "https": f"http://{auth}"}
    except: return None

def _jitter(a=0.5, b=1.5):
    time.sleep(random.uniform(a, b))

def _take_screenshot_playwright(page, job_name):
    try:
        if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"_DEBUG_{job_name}_{timestamp}.png"
        filepath = os.path.join(LOG_DIR, filename)
        page.screenshot(path=filepath, full_page=True)
        print(f"[debug] 📸 Screenshot saved: {filepath}")
    except: pass

# =========================
# AUTHENTICATION BRIDGE
# =========================

def get_auth_cookies_from_profile() -> Dict:
    if not os.path.exists(MASTER_PROFILE_DIR):
        print("[auth] ⚠️ Không tìm thấy profile gốc. Chạy chế độ Guest.")
        return {}

    temp_auth_path = os.path.join(SCRIPT_DIR, "udemy_profile_auth_temp")
    if os.path.exists(temp_auth_path): shutil.rmtree(temp_auth_path, ignore_errors=True)
    try:
        shutil.copytree(MASTER_PROFILE_DIR, temp_auth_path, dirs_exist_ok=True)
        lock = os.path.join(temp_auth_path, "SingletonLock")
        if os.path.exists(lock): os.remove(lock)
    except Exception as e:
        print(f"[auth] ❌ Lỗi copy profile: {e}")
        return {}

    cookies_dict = {}
    playwright = None
    context = None
    
    try:
        print("[auth] 🔐 Đang trích xuất Cookie...")
        playwright = sync_playwright().start()
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=temp_auth_path,
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        cookies = context.cookies("https://www.udemy.com")
        for c in cookies:
            cookies_dict[c['name']] = c['value']
        
        print(f"[auth] ✅ Đã lấy được {len(cookies_dict)} cookies.")
    except Exception as e:
        print(f"[auth] ⚠️ Lỗi lấy cookie: {e}")
    finally:
        try:
            if context: context.close()
            if playwright: playwright.stop()
            if os.path.exists(temp_auth_path): shutil.rmtree(temp_auth_path, ignore_errors=True)
        except: pass
        
    return cookies_dict

# =========================
# GIAI ĐOẠN 1: PLAYWRIGHT
# =========================

def _human_scroll_playwright(page):
    for _ in range(SCROLL_STEPS):
        scroll_amount = random.randint(400, 800)
        page.evaluate(f"window.scrollBy(0, {scroll_amount});")
        time.sleep(random.uniform(0.4, 0.8)) 
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    _jitter()

def _extract_course_links_from_html(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    links = set()
    
    start_node = None
    candidates = soup.find_all(['h2', 'h1', 'div', 'span'])
    for tag in candidates:
        text = tag.get_text(strip=True)
        if text.startswith("All ") and text.endswith(" courses"):
            start_node = tag
            break
            
    source_tags = []
    if start_node:
        source_tags = start_node.find_all_next('a', href=True)
    else:
        source_tags = soup.select('a[href*="/course/"]')

    for a in source_tags:
        href = a.get("href") or ""
        if "/course/" in href:
            if href.startswith("/"): href = "https://www.udemy.com" + href
            href = href.split("?")[0].rstrip("/") + "/"
            if href.startswith("https://www.udemy.com/course/"):
                links.add(href)
                
    return sorted(list(links))

def get_course_urls_per_page_playwright(listing_url: str, headless: bool = True) -> List[str]:
    url_hash = hashlib.md5(listing_url.encode()).hexdigest()[:8]
    profile_path = os.path.join(SCRIPT_DIR, f"udemy_profile_pw_{url_hash}")
    
    if os.path.exists(profile_path):
        lock_file = os.path.join(profile_path, "SingletonLock")
        if os.path.exists(lock_file):
            try: os.remove(lock_file)
            except: pass
    else:
        os.makedirs(profile_path)
    
    playwright_instance = None
    context = None
    final_links = []
    
    try:
        # [SỬA LỖI] Lấy Proxy và ép vào định dạng Playwright
        proxy_settings = None
        raw_p = get_proxies()
        if raw_p and "http" in raw_p:
            p_url = raw_p["http"]
            if "@" in p_url:
                try:
                    _auth_part, _host_part = p_url.replace("http://", "").replace("https://", "").split("@")
                    _user, _pwd = _auth_part.split(":")
                    proxy_settings = {"server": f"http://{_host_part}", "username": _user, "password": _pwd}
                except: pass
            else:
                proxy_settings = {"server": p_url}

        playwright_instance = sync_playwright().start()
        
        launch_args = {
            "user_data_dir": profile_path,
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-dev-shm-usage", "--window-size=1920,1080"],
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1920, "height": 1080}
        }
        if proxy_settings:
            launch_args["proxy"] = proxy_settings
            print(f"[driver-pw] 🛡️ Áp dụng Proxy: {proxy_settings['server']}")

        context = playwright_instance.chromium.launch_persistent_context(**launch_args)
        page = context.new_page()
        page.set_default_timeout(PAGELOAD_TIMEOUT * 1000)
        
        for attempt in range(1, 3):
            try:
                print(f"[driver-pw] 🌍 Mở trang (Lần {attempt}): {listing_url}")
                if attempt == 1: page.goto(listing_url, wait_until="domcontentloaded")
                else: page.reload(wait_until="domcontentloaded")
                
                print("[wait] ⏳ Chờ thẻ khóa học...")
                try:
                    page.wait_for_selector('h3 a[href*="/course/"]', state="attached", timeout=ELEMENT_TIMEOUT)
                except: pass

                _jitter()
                _human_scroll_playwright(page)
                try: page.wait_for_load_state("networkidle", timeout=ELEMENT_TIMEOUT)
                except: pass
                
                html = page.content()
                links = _extract_course_links_from_html(html)
                
                final_links = links
                if len(links) >= 5:
                    print(f"[category] ✅ Tìm thấy {len(links)} khóa học.")
                    break
                else:
                    print(f"[category] ⚠️ Tìm thấy {len(links)} link.")
                    if attempt == 2: _take_screenshot_playwright(page, "EMPTY_FINAL")
            except Exception as e:
                print(f"[driver-pw] ❌ Lỗi: {e}")
                time.sleep(3)
    except Exception as e:
        print(f"[FATAL ERROR] ☠️ Playwright Crash: {e}")
    finally:
        try:
            if context: context.close()
            if playwright_instance: playwright_instance.stop()
            if os.path.exists(profile_path): shutil.rmtree(profile_path, ignore_errors=True)
        except: pass
        
    return final_links

# =========================
# GIAI ĐOẠN 2: PARSING (V35/V38 - ULTIMATE)
# =========================

def _clean_price_str(price_str: str) -> Optional[float]:
    if not price_str: return None
    try:
        txt = price_str.replace("Free", "0").replace("₫", "").replace("$", "").strip()
        if "," in txt: txt = txt.replace(",", "") 
        match = re.search(r"(\d+(\.\d+)?)", txt)
        if match: return float(match.group(1))
        return None
    except: return None

def _extract_price_data(soup: BeautifulSoup, data_json: Dict) -> Tuple[Optional[float], Optional[float]]:
    found_prices = []

    # 1. Meta Tag
    try:
        meta_price = soup.find("meta", {"property": "udemy_com:price"})
        if meta_price:
            p = _clean_price_str(meta_price.get("content", ""))
            if p is not None: found_prices.append(p)
    except: pass

    # 2. JSON-LD
    try:
        script_tag = soup.find("script", {"type": "application/ld+json"})
        if script_tag:
            json_ld = json.loads(script_tag.string)
            items_to_check = []
            
            if isinstance(json_ld, dict):
                if "@graph" in json_ld:
                    items_to_check = json_ld["@graph"]
                else:
                    items_to_check = [json_ld]
            elif isinstance(json_ld, list):
                items_to_check = json_ld
                
            for item in items_to_check:
                if item.get("@type") in ["Course", "Product"]:
                    offers = item.get("offers", [])
                    if isinstance(offers, dict): offers = [offers]
                    for offer in offers:
                        p = float(offer.get("price", 0))
                        if p > 0: found_prices.append(p)
    except: pass

    # 3. Data Module
    try:
        course_data = data_json.get('serverSideProps', {}).get('course', {}) or \
                      data_json.get('componentProps', {}).get('course', {}) or \
                      data_json.get('portal_data', {}).get('course', {})
        
        if 'price_text_data' in course_data:
            ptd = course_data['price_text_data']
            if 'amount' in ptd: found_prices.append(float(ptd['amount']))
            if 'list_price' in ptd and 'amount' in ptd['list_price']: 
                found_prices.append(float(ptd['list_price']['amount']))
        
        if 'discount' in course_data:
            d = course_data['discount']
            if 'list_price' in d and 'amount' in d['list_price']:
                found_prices.append(float(d['list_price']['amount']))
        
        if 'base_price' in course_data:
            bp = course_data['base_price']
            if 'amount' in bp: found_prices.append(float(bp['amount']))
    except: pass

    # 4. HTML Text Fallback
    try:
        price_divs = soup.select('div[data-purpose="course-price-text"] span')
        for div in price_divs:
            text = div.get_text(strip=True)
            if any(c.isdigit() for c in text):
                p = _clean_price_str(text)
                if p is not None and p > 0: found_prices.append(p)
    except: pass

    valid_prices = sorted(list(set([p for p in found_prices if p is not None])))
    
    if not valid_prices: return None, None
    
    if len(valid_prices) == 1:
        return valid_prices[0], valid_prices[0]
    else:
        return max(valid_prices), min(valid_prices)

def parse_course_details(html_content: str) -> Optional[Dict]:
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        body_tag = soup.find('body')
        next_tag = soup.find('script', id='__NEXT_DATA__')
        
        data = {}
        course_data = None
        reviews_data = None
        
        if body_tag and 'data-module-args' in body_tag.attrs:
            data = json.loads(body_tag['data-module-args'])
            course_data = data.get('serverSideProps', {}).get('course', {}) or \
                          data.get('componentProps', {}).get('course', {}) or \
                          data.get('portal_data', {}).get('course', {})
            reviews_data = data.get('serverSideProps', {}).get('reviewsRatings', {}) or \
                           data.get('componentProps', {}).get('reviews', {})
        elif next_tag:
            n_data = json.loads(next_tag.string)
            data = n_data.get('props', {}).get('pageProps', {})
            course_data = data.get('course', {})
            reviews_data = data.get('reviews', {})
        script_tag = soup.find('script', type='application/ld+json')
        if script_tag and not course_data:
            try:
                json_ld = json.loads(script_tag.string)
                items = json_ld.get('@graph', [json_ld]) if isinstance(json_ld, dict) else json_ld
                for item in items:
                    if item.get('@type') in ['Course', 'Product']:
                        course_data = {
                            'title': item.get('name', ''),
                            'url': item.get('url', ''),
                            'isPaid': not item.get('isAccessibleForFree', False),
                            'headline': item.get('description', ''),
                            'visibleInstructors': [{'title': p.get('name', '')} for p in item.get('hasCourseInstance', {}).get('instructor', [])],
                            'estimatedContentLength_text': item.get('hasCourseInstance', {}).get('courseWorkload', ''),
                            'localeSimpleEnglishTitle': item.get('inLanguage'),
                            'instructionalLevel': item.get('educationalLevel'),
                            'lastUpdateDate': item.get('datePublished', '')
                        }
                        if not course_data['visibleInstructors']:
                            if item.get('provider', {}).get('name'):
                                course_data['visibleInstructors'] = [{'title': item.get('provider').get('name')}]
                            elif item.get('author'):
                                au = item.get('author', [{}])
                                course_data['visibleInstructors'] = [{'title': a.get('name', '')} for a in au]
                        
                        reviews_data = {
                            'averageRating': item.get('aggregateRating', {}).get('ratingValue', 0),
                            'numberOfReviews': item.get('aggregateRating', {}).get('ratingCount', 0)
                        }
                        break
            except Exception as e: pass

        if not course_data: return None

        import re
        course_id = data.get('course_id')
        if not course_id:
            cm = re.search(r'courseId[^\d]*(\d{5,8})', html_content)
            course_id = cm.group(1) if cm else None

        title = course_data.get('title')
        if not title:
            tm = re.search(r'<title.*?>(.*?)</title>', html_content)
            title = tm.group(1).replace(' | Udemy', '').replace('&trade;', '™').strip() if tm else None
        
        instructors_list = []
        if 'instructors' in course_data and 'instructors_info' in course_data['instructors']:
            instructors_list = course_data['instructors']['instructors_info']
        elif 'visible_instructors' in course_data:
            instructors_list = course_data['visible_instructors']
        elif 'visibleInstructors' in course_data:
            instructors_list = course_data['visibleInstructors']
        elif 'instructors' in course_data and isinstance(course_data['instructors'], list):
            instructors_list = course_data['instructors']

        all_instructors = []
        for instructor in instructors_list or []:
            all_instructors.append({
                'instructor_id': instructor.get('id'),
                'name': instructor.get('display_name') or instructor.get('title'),
                'job_title': instructor.get('job_title'),
                'num_students': instructor.get('total_num_students') or instructor.get('num_students'),
                'avg_rating_score': instructor.get('avg_rating_recent') or instructor.get('rating'),
                'num_of_courses': instructor.get('total_num_taught_courses') or instructor.get('num_published_courses'),
                'total_num_reviews': instructor.get('total_num_reviews') or instructor.get('num_reviews')
            })

        original_price, discount_price = _extract_price_data(soup, data)
        
        rating_dist = {}
        try:
            raw_dist = reviews_data.get('ratingDistribution', []) if reviews_data else []
            if raw_dist: rating_dist = json.dumps(raw_dist) 
        except: pass

        # Regex Fallbacks cho Dữ liệu Tĩnh
        num_students = course_data.get('numStudents') or course_data.get('num_students')
        if not num_students:
            s_tag = soup.find(attrs={'data-purpose': 'enrollment'})
            if not s_tag: s_tag = soup.find(class_=re.compile(r'enrollment-count'))
            if s_tag:
                student_m = re.search(r'([\d,\.]+)', s_tag.text)
                if student_m: num_students = int(student_m.group(1).replace(',', '').replace('.', ''))
            
        avg_rating = course_data.get('rating')
        if not avg_rating and reviews_data: avg_rating = reviews_data.get('averageRating')
        if not avg_rating:
            r_tag = soup.find(attrs={'data-purpose': 'rating-number'})
            if r_tag:
                rating_m = re.search(r'([\d\.]+)', r_tag.text)
                if rating_m: avg_rating = float(rating_m.group(1))
            
        num_reviews = course_data.get('numReviews') or course_data.get('num_reviews')
        if not num_reviews and reviews_data: num_reviews = reviews_data.get('numberOfReviews')
        if not num_reviews:
            r_cnt = soup.find('a', attrs={'data-purpose': 'rating'})
            if r_cnt:
                reviews_m = re.search(r'([\d,\.]+)', r_cnt.text)
                if reviews_m: num_reviews = int(reviews_m.group(1).replace(',', '').replace('.', ''))

        duration_sec = course_data.get('contentLengthVideo') or course_data.get('content_length_video')
        if not duration_sec:
            raw_dur = str(course_data.get('estimatedContentLength_text', ''))
            if raw_dur.startswith('PT'):
                h = re.search(r'(\d+)H', raw_dur); m = re.search(r'(\d+)M', raw_dur); s = re.search(r'(\d+)S', raw_dur)
                duration_sec = (int(h.group(1)) if h else 0) * 3600 + (int(m.group(1)) if m else 0) * 60 + (int(s.group(1)) if s else 0)

        pub_date = course_data.get('publishedDate') or course_data.get('published_time') or course_data.get('lastUpdateDate')

        return {
            'course_data': {
                'course_id': course_id, 
                'title': title,
                'headline': course_data.get('headline'),
                'language': course_data.get('localeSimpleEnglishTitle'),
                'level': course_data.get('instructionalLevel') or course_data.get('instructional_level_simple'),
                'course_duration_seconds': duration_sec,
                'publishes_date': pub_date,
                'lasted_updated_date': course_data.get('lastUpdateDate') or course_data.get('last_update_date'),
                'original_price': original_price,
                'discount_price': discount_price,
                'num_students': num_students,
                'num_reviews': num_reviews,
                'avg_rating_score': avg_rating,
                'rating_distribution': rating_dist
            },
            'instructors': all_instructors
        }
    except: return None

def parse_course_price_only(html_content: str) -> Optional[Dict]:
    try:
        soup = BeautifulSoup(html_content, 'lxml')
        body_tag = soup.find('body')
        next_tag = soup.find('script', id='__NEXT_DATA__')
        
        data = {}
        course_id = None
        title = None
        
        # Method 1: Body attributes
        if body_tag and body_tag.get('data-clp-course-id'):
            course_id = body_tag.get('data-clp-course-id')
            title = soup.title.string.replace(' | Udemy', '').strip() if soup.title else 'N/A'
            
        # Method 2: Regex for Raw HTML (NextJS Stream without DOM JS Evaluation)
        if not course_id:
            import re
            m = re.search(r'courseId[^\d]*(\d{5,8})', html_content)
            if m: course_id = m.group(1)
            tm = re.search(r'<title.*?>(.*?)</title>', html_content)
            if tm: title = tm.group(1).replace(' | Udemy', '').replace('&trade;', '™').strip()
             
        # Method 3: Old Format
        if body_tag and 'data-module-args' in body_tag.attrs:
            data = json.loads(body_tag['data-module-args'])
            course_id = course_id or data.get('course_id')
            title = title or data.get('title')
        elif next_tag:
            n_data = json.loads(next_tag.string)
            data = n_data.get('props', {}).get('pageProps', {}).get('course', {})
            course_id = course_id or data.get('id')
            title = title or data.get('title')
            
        if not course_id: return None
        original_price, discount_price = _extract_price_data(soup, data)

        return {
            'course_id': course_id, 
            'title': title, 
            'original_price': original_price, 
            'discount_price': discount_price
        }
    except: return None

def run_course_parsing_loop(course_urls: List[str], category_name: str, parser_func, cookies: Dict = None) -> List[Dict]:
    results = []
    impersonate_id = random.choice(IMPERSONATE_PROFILES)
    proxy_dict = get_proxies()
    session = Session(impersonate=impersonate_id, proxies=proxy_dict, cookies=cookies) 

    for i, url in enumerate(course_urls, 1):
        success = False
        for attempt in range(3):
            try:
                r = session.get(url, timeout=20)
                if r.status_code == 200:
                    parsed = parser_func(r.text)
                    if parsed:
                        # FALLBACK BẮT GIÁ TIỀN QUA API CỦA UDEMY NẾU TRÊN HTML BỊ GIẤU
                        c_id = parsed.get('course_id') or parsed.get('course_data', {}).get('course_id')
                        tgt = parsed if 'original_price' in parsed else parsed.get('course_data', {})
                        
                        if c_id:
                            orig_p = tgt.get('original_price')
                            disc_p = tgt.get('discount_price')
                            
                            if orig_p is None or disc_p is None or orig_p == disc_p:
                                try:
                                    headers = {}
                                    if cookies and 'access_token' in cookies:
                                        headers['Authorization'] = f"Bearer {cookies['access_token']}"
                                        
                                    p_url = f"https://www.udemy.com/api-2.0/pricing/?course_ids={c_id}&fields[pricing_result]=price,discount_price,list_price"
                                    pr = session.get(p_url, headers=headers, timeout=10)
                                    if pr.status_code == 200:
                                        p_data = pr.json().get('courses', {}).get(str(c_id), {})
                                        list_obj = p_data.get('list_price') or {}
                                        disc_obj = p_data.get('discount_price') or {}
                                        curr_obj = p_data.get('price') or {}
                                        
                                        list_p = list_obj.get('amount')
                                        disc_p_api = disc_obj.get('amount')
                                        curr_p = curr_obj.get('amount')
                                        
                                        if list_p is not None: tgt['original_price'] = float(list_p)
                                        elif curr_p is not None: tgt['original_price'] = float(curr_p)
                                        
                                        if disc_p_api is not None: tgt['discount_price'] = float(disc_p_api)
                                        elif curr_p is not None and tgt.get('original_price') and float(curr_p) < tgt['original_price']:
                                            tgt['discount_price'] = float(curr_p)
                                        elif curr_p is not None:
                                            tgt['discount_price'] = float(curr_p)
                                except: pass

                        # FALLBACK BẮT INFO TÁC GIẢ QUA API UDEMY NẾU HTML KHÔNG CÓ
                        if c_id and 'instructors' in parsed:
                            try:
                                inst_url = f"https://www.udemy.com/api-2.0/courses/{c_id}/?fields[course]=visible_instructors&fields[user]=title,job_title,avg_rating_recent,total_num_taught_courses,total_num_students,total_num_reviews"
                                ir = session.get(inst_url, timeout=10)
                                if ir.status_code == 200:
                                    api_insts = ir.json().get('visible_instructors', [])
                                    if api_insts:
                                        full_insts = []
                                        for api_i in api_insts:
                                            full_insts.append({
                                                'instructor_id': api_i.get('id'),
                                                'name': api_i.get('title'),
                                                'job_title': api_i.get('job_title'),
                                                'num_students': api_i.get('total_num_students'),
                                                'avg_rating_score': api_i.get('avg_rating_recent'),
                                                'num_of_courses': api_i.get('total_num_taught_courses'),
                                                'total_num_reviews': api_i.get('total_num_reviews')
                                            })
                                        parsed['instructors'] = full_insts
                            except: pass

                        if 'course_data' in parsed:
                            parsed['course_data']["_url"] = url
                            parsed['course_data']["_category"] = category_name
                            parsed['course_data']["_scraped_datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        else:
                            parsed["_url"] = url
                            parsed["_category"] = category_name
                            parsed["_scraped_datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        results.append(parsed)
                        success = True
                        time.sleep(random.uniform(0.1, 0.3))
                        break
            except Exception as e:
                pass
            
            # Chỉ khi lỗi hoặc bị block thì mới khởi tạo lại session cho lần thử tiếp
            if not success and attempt < 2:
                try: session.close()
                except: pass
                # Đổi impersonate mạnh hơn và thử lại
                impersonate_id = random.choice(IMPERSONATE_PROFILES)
                session = Session(impersonate=impersonate_id, proxies=proxy_dict)
                time.sleep(1)

        if not success: 
            print(f"  [SKIP] {url} (Blocked/No Data/Timeout)")
            if not os.path.exists(LOG_DIR): os.makedirs(LOG_DIR)
            try:
                with open(os.path.join(LOG_DIR, "debug_skip.html"), "w", encoding="utf-8") as f:
                    f.write(r.text if 'r' in locals() and hasattr(r, 'text') else "No response")
            except: pass
            
    try: session.close()
    except: pass
    return results

def save_batch_to_minio(batch_data: List[Dict], job_type: str, group_name: str, start_p: int, end_p: int, s3_client, bucket_name: str, test_mode: bool):
    import pandas as pd
    if not batch_data: return
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = "TEST" if test_mode else "PROD"
    page_range = f"p{start_p}-{end_p}"
    prefix_name = f"{mode}_{job_type}_{group_name}_{page_range}_{timestamp}"
    
    print(f"\n[minio] 🪣 Đang upload: {prefix_name} ({len(batch_data)} khóa)...")
    try:
        courses_list = []
        instructors_list = []
        for row in batch_data:
            if 'course_data' in row:
                c_data = row['course_data']
                c_id = c_data.get('course_id')
                if not c_id: continue
                courses_list.append(c_data)
                insts = row.get('instructors', [])
                for inst in insts:
                    inst['course_id'] = c_id
                    instructors_list.append(inst)
            else:
                courses_list.append(row)

        if courses_list:
            df = pd.json_normalize(courses_list)
            for col in df.columns:
                if df[col].apply(type).isin([dict, list]).any():
                    df[col] = df[col].apply(json.dumps)
            
            # Đảm bảo các cột dạng số được ép kiểu chuẩn tránh lỗi Parquet Convert
            num_cols = ['original_price', 'discount_price', 'num_students', 'num_reviews', 'avg_rating_score', 'course_duration_seconds']
            for col in num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

            # --- LƯU LOCAL FILE ---
            local_path = os.path.join(LOG_DIR, f"{prefix_name}_courses.parquet")
            df.to_parquet(local_path, compression='gzip', index=False)
            print(f"[local] 💾 Đã lưu local: {local_path}")
            
            # --- UPLOAD CLOUD ---
            s3_key = f"{job_type}/{prefix_name}_courses.parquet"
            s3_client.upload_file(local_path, bucket_name, s3_key)
            print(f"[minio] ✅ Upload hoàn tất: {s3_key}")

        if instructors_list:
            df = pd.DataFrame(instructors_list)
            
            # Đảm bảo các cột dạng số được ép kiểu chuẩn
            inst_num_cols = ['num_students', 'avg_rating_score', 'num_of_courses', 'total_num_reviews']
            for col in inst_num_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').astype('float64')

            # --- LƯU LOCAL FILE ---
            local_path = os.path.join(LOG_DIR, f"{prefix_name}_instructors.parquet")
            df.to_parquet(local_path, compression='gzip', index=False)
            print(f"[local] 💾 Đã lưu local: {local_path}")
            
            # --- UPLOAD CLOUD ---
            s3_key = f"{job_type}/{prefix_name}_instructors.parquet"
            s3_client.upload_file(local_path, bucket_name, s3_key)
            print(f"[minio] ✅ Upload hoàn tất: {s3_key}")
    except Exception as e:
        print(f"[minio] ❌ Upload Failed: {e}")

CATEGORIES_FULL = {
    "Web Development": "https://www.udemy.com/courses/development/web-development/",
    "Data Science": "https://www.udemy.com/courses/development/data-science/",
    "Mobile Development": "https://www.udemy.com/courses/development/mobile-apps/",
    "Programming Languages": "https://www.udemy.com/courses/development/programming-languages/",
    "Game Development": "https://www.udemy.com/courses/development/game-development/",
    "Database Design & Development": "https://www.udemy.com/courses/development/databases/",
    "Software Testing": "https://www.udemy.com/courses/development/software-testing/",
    "Software Engineering": "https://www.udemy.com/courses/development/software-engineering/",
    "Software Development Tools": "https://www.udemy.com/courses/development/development-tools/",
    "No-Code Development": "https://www.udemy.com/courses/development/no-code-development/"
}

CATEGORY_GROUPS = {
    "group1": ["Web Development", "Software Engineering"],
    "group2": ["Programming Languages", "Database Design & Development", "Software Testing", "No-Code Development"],
    "group3": ["Data Science", "Mobile Development", "Game Development", "Software Development Tools"], 
}

def run_job_with_page_batching(job_type: str, group_name: str, categories: Dict, headless: bool, s3_client, bucket_name: str, test_mode: bool, start_page_override: int = 1):
    print(f"--- BẮT ĐẦU JOB: {job_type} (Group: {group_name} | Start: {start_page_override}) ---")
    print(f"[debug] Target Bucket: {bucket_name}")
    
    auth_cookies = get_auth_cookies_from_profile()
    if auth_cookies: print(f"[system] ✅ Auth Cookies Loaded ({len(auth_cookies)} items).")
    else: print(f"[system] ⚠️ Running as GUEST (No Cookies).")

    parser_func = parse_course_details if job_type == 'dashboard' else parse_course_price_only
    max_total_pages = 9999
    
    for cat_name, url in categories.items():
        print(f"\n>>> CATEGORY: {cat_name}")
        current_page = start_page_override
        low_data_streak = 0
        while current_page <= max_total_pages:
            start_p = current_page
            end_p = current_page + PAGES_PER_BATCH
            
            if test_mode and start_p > start_page_override + 2: 
                print("🛑 TEST MODE: Dừng sau 2 trang.")
                break

            print(f"\n[phase-1] 🕸️ Gom link trang {start_p} -> {end_p - 1}...")
            batch_urls = []
            actual_last_page = start_p
            for p in range(start_p, end_p):
                actual_last_page = p
                if test_mode and p >= start_page_override + 2: 
                    print(f"🛑 TEST MODE: Đã đủ 2 trang.")
                    break
                links = get_course_urls_per_page_playwright(f"{url}?p={p}", headless)
                if len(links) < 16:
                    low_data_streak += 1
                    print(f"⚠️ Trang {p} thiếu dữ liệu: {len(links)} link. (Streak: {low_data_streak}/{MAX_CONSECUTIVE_LOW_DATA})")
                    if links:
                        new_links = [l for l in links if l not in batch_urls]
                        batch_urls.extend(new_links)
                    if low_data_streak >= MAX_CONSECUTIVE_LOW_DATA:
                        print(f"🛑 Dừng Category '{cat_name}'.")
                        current_page = 999999 
                        break
                else:
                    low_data_streak = 0
                    new_links = [l for l in links if l not in batch_urls]
                    batch_urls.extend(new_links)
                    print(f"-> Page {p}: +{len(new_links)} links")
            
            unique_batch = sorted(list(set(batch_urls)))
            if len(unique_batch) > 0:
                print(f"\n[phase-2] 🚀 Parse & Save {len(unique_batch)} khóa học...")
                full_results = []
                chunk_size = 50
                for i in range(0, len(unique_batch), chunk_size):
                    chunk = unique_batch[i : i + chunk_size]
                    res = run_course_parsing_loop(chunk, cat_name, parser_func, cookies=auth_cookies)
                    full_results.extend(res)
                    print(f"  -> Progress: {min(i+chunk_size, len(unique_batch))}/{len(unique_batch)}")
                
                if not full_results:
                    print(f"\n[system] ⚠️ CẢNH BÁO TỐT TỐC: Danh sách kết quả trống trơn sau khi parse {len(unique_batch)} links!\n  👉 Nguyên nhân: Tool gọi quá nhanh nên bị Cloudflare chặn ngầm (Error 403) tại các link chi tiết.")
                
                save_batch_to_minio(full_results, job_type, group_name, start_p, actual_last_page, s3_client, bucket_name, test_mode)
                del batch_urls, unique_batch, full_results
                gc.collect()
                print("[system] 🧹 RAM Cleaned.")
            if current_page != 999999: current_page = end_p

    print("\n--- [HOÀN TẤT JOB] ---")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--job", required=True, choices=['dashboard', 'tracker'])
    parser.add_argument("--test", action="store_true")
    parser.add_argument("--group", choices=["group1", "group2", "group3"])
    parser.add_argument("--category", type=str, help="Chạy riêng lẻ 1 category cụ thể")
    parser.add_argument("--start-page", type=int, default=1)
    args = parser.parse_args()
    
    load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
    s3_client = boto3.client('s3',
        endpoint_url=os.getenv("MINIO_ENDPOINT_URL", "http://localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        config=Config(signature_version='s3v4')
    )
    BUCKET_NAME = "udemy123"
    IS_HEADLESS = os.environ.get("IS_HEADLESS", "false").lower() == "true"
    
    cats_to_run = {}
    group_name_run = "custom"
    
    if args.category:
        if args.category in CATEGORIES_FULL:
            cats_to_run = {args.category: CATEGORIES_FULL[args.category]}
            group_name_run = f"cat_{args.category.replace(' ', '_')}"
        else:
            print(f"❌ Error: Category '{args.category}' not found!")
            sys.exit(1)
    elif args.job == 'dashboard':
        if args.group:
            group_name_run = args.group
            group_cats = CATEGORY_GROUPS.get(args.group, [])
            cats_to_run = {k:v for k,v in CATEGORIES_FULL.items() if k in group_cats}
        else:
            group_name_run = "all"
            cats_to_run = CATEGORIES_FULL
    else:
        # [FLEXIBLE TRACKER LOGIC]
        # Bây giờ Tracker cũng có thể chạy theo Group hoặc Category
        if args.group:
             group_name_run = f"tracker_{args.group}"
             group_cats = CATEGORY_GROUPS.get(args.group, [])
             cats_to_run = {k:v for k,v in CATEGORIES_FULL.items() if k in group_cats}
        else:
             # Mặc định cũ (nếu không có tham số gì)
             group_name_run = "tracker_nocode"
             cats_to_run = {"No-Code Development": CATEGORIES_FULL["No-Code Development"]}
        
    run_job_with_page_batching(args.job, group_name_run, cats_to_run, IS_HEADLESS, s3_client, BUCKET_NAME, args.test, args.start_page)