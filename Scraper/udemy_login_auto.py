# udemy_login_auto.py
"""
Tự động login Udemy bằng Playwright.
FIXED:
1. Đã thêm load_dotenv để đọc file .env (Tránh lỗi thiếu Email/Pass).
2. Đã chỉnh mặc định IS_HEADLESS = false để hiện trình duyệt khi chạy tay.
"""

import os
import sys
import time
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

if sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# --- [FIX QUAN TRỌNG] THÊM ĐOẠN NÀY ĐỂ ĐỌC FILE .ENV ---
try:
    from dotenv import load_dotenv
    # Load file .env từ thư mục hiện tại
    load_dotenv()
except ImportError:
    print("[WARN] Chưa cài python-dotenv. Nếu chạy Docker thì không sao.")
# -------------------------------------------------------


def _is_already_logged_in(page) -> bool:
    """Kiểm tra một vài dấu hiệu đã login."""
    selectors = [
        'a[data-purpose="user-dropdown"]',
        'button[data-purpose="user-dropdown"]',
        'div[data-purpose="user-dropdown"]',
        'a[href*="/home/my-courses/"]',
        'a:has-text("My learning")',
        'a:has-text("My courses")',
    ]
    for sel in selectors:
        try:
            loc = page.locator(sel)
            if loc.count() > 0 and loc.first.is_visible():
                return True
        except Exception:
            continue
    return False


def _dismiss_cookie_banner(page):
    """Thử đóng banner cookie / consent nếu có."""
    candidates = [
        'button:has-text("Accept all cookies")',
        'button:has-text("Accept All Cookies")',
        'button:has-text("Got it")',
        'button:has-text("I agree")',
        'button:has-text("Tôi hiểu")',
    ]
    for sel in candidates:
        try:
            btn = page.locator(sel)
            if btn.count() > 0 and btn.first.is_visible():
                print(f"[UDEMY LOGIN] 🍪 Thấy cookie banner ({sel}), click đóng...")
                btn.first.click()
                page.wait_for_timeout(1000)
                return
        except Exception:
            continue


def _safe_goto(page, url: str, label: str = ""):
    try:
        print(f"[UDEMY LOGIN] 🌐 Mở {label or url} ...")
        page.goto(url, wait_until="load", timeout=60000)
    except PlaywrightTimeoutError:
        print(f"[UDEMY LOGIN] ⚠️ Timeout khi mở {label or url}, tiếp tục...")
    except Exception as e:
        print(f"[UDEMY LOGIN] ❌ Lỗi khi mở {label or url}: {e}")


def ensure_udemy_logged_in(headless: bool = True) -> None:
    email = os.getenv("UDEMY_EMAIL")
    password = os.getenv("UDEMY_PASSWORD")
    
    # Chỉnh lại đường dẫn profile (ưu tiên tuyệt đối từ script dir nếu là relative)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_profile = os.getenv("UDEMY_PROFILE_DIR")
    
    if env_profile:
        if not os.path.isabs(env_profile):
            profile_dir = os.path.join(script_dir, env_profile)
        else:
            profile_dir = env_profile
    else:
        # Mặc định theo hệ điều hành
        if os.name == 'nt': 
            profile_dir = os.path.join(script_dir, "udemy_profile")
        else:
            profile_dir = "/opt/airflow/udemy_profile"

    if not email or not password:
        print("[UDEMY LOGIN] ❌ Thiếu UDEMY_EMAIL hoặc UDEMY_PASSWORD. Hãy kiểm tra file .env")
        return

    print(f"[UDEMY LOGIN] 🔐 Dùng profile dir: {profile_dir}")
    print(f"[UDEMY LOGIN] 👤 Email: {email}")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=headless, # True: Ẩn, False: Hiện
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--window-size=1920,1080",
            ],
        )

        context.set_default_timeout(60000)
        page = context.new_page()

        # 1. Vào trang chủ
        _safe_goto(page, "https://www.udemy.com/", label="trang chủ Udemy")
        page.wait_for_timeout(3000)
        _dismiss_cookie_banner(page)

        if _is_already_logged_in(page):
            print("[UDEMY LOGIN] ✅ Đã login sẵn, dùng lại session.")
            time.sleep(2)
            context.close()
            return

        print("[UDEMY LOGIN] ℹ️ Chưa login. Bắt đầu auto login...")

        # 2. Mở trang login
        _safe_goto(
            page,
            "https://www.udemy.com/join/login-popup/?locale=en_US",
            label="trang login",
        )
        page.wait_for_timeout(3000)
        _dismiss_cookie_banner(page)

        # 3. Điền form (Multi-step flow)
        try:
            print("[UDEMY LOGIN] ⌛ Đợi input email...")
            email_input = page.wait_for_selector('input[name="email"]', timeout=30000)
            print("[UDEMY LOGIN] ✏️ Điền email...")
            email_input.fill(email)
            
            print("[UDEMY LOGIN] 👉 Click nút Continue...")
            # Thử nhiều selector cho nút Continue
            continue_btn = page.locator('button[data-purpose="continue-button"], button:has-text("Continue"), button[type="submit"]').first
            
            if continue_btn.count() > 0:
                continue_btn.click()
            else:
                print("[UDEMY LOGIN] ⚠️ Không tìm thấy nút bằng selector, thử nhấn Enter...")
                page.keyboard.press("Enter")
            
            # Chờ trang chuyển sang bước nhập password (tăng timeout)
            page.wait_for_timeout(3000)
            
            print("[UDEMY LOGIN] ⌛ Đợi input password...")
            pwd_input = page.wait_for_selector('input[name="password"]', timeout=30000)
            print("[UDEMY LOGIN] ✏️ Điền password...")
            pwd_input.fill(password)

            print("[UDEMY LOGIN] 👉 Click nút Sign In...")
            submit_btn = page.locator(
                'button[type="submit"], button[data-purpose="login-submit-button"]'
            ).first
            submit_btn.click()
        except Exception as e:
            print(f"[UDEMY LOGIN] ❌ Lỗi thao tác: {e}")
            print("👉 Hãy thử điền tay trên trình duyệt đang mở...")

        # 4. Chờ login thủ công (nếu cần)
        print("[UDEMY LOGIN] ⏳ Đang chờ đăng nhập thành công (Tối đa 2 phút)...")
        print("⚠️ NẾU THẤY CAPTCHA, HÃY GIẢI BẰNG TAY TRÊN TRÌNH DUYỆT NGAY!")
        
        for _ in range(24): # Chờ 120s
            if _is_already_logged_in(page):
                break
            page.wait_for_timeout(5000)

        if _is_already_logged_in(page):
            print(f"[UDEMY LOGIN] ✅ Login thành công! Session đã lưu tại: {profile_dir}")
        else:
            print("[UDEMY LOGIN] ⚠️ Hết giờ. Chưa login được.")

        context.close()

if __name__ == "__main__":
    # [CẤU HÌNH CHO DOCKER]
    # Khi chạy trong Docker, biến môi trường IS_HEADLESS thường là "false" (để dùng xvfb)
    # Nhưng với script này, ta cứ để code tự quyết định dựa trên env
    is_headless = os.environ.get("IS_HEADLESS", "false").lower() == "true"
    
    # Chạy login
    ensure_udemy_logged_in(headless=is_headless)