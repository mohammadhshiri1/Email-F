#!/usr/bin/env python3
"""
ایمیل موقت بدون نیاز به ثبت‌نام – مناسب برای گیت‌هاب اکشن
با استفاده از API عمومی mail.tm
"""

import os
import sys
import time
import re
import json
import random
import string
import requests

# ---------- تنظیمات ----------
WAIT_TIMEOUT = 180        # حداکثر زمان انتظار برای دریافت ایمیل (ثانیه)
POLL_INTERVAL = 5         # فاصله بررسی صندوق (ثانیه)
USERNAME_LENGTH = 10      # طول نام کاربری تصادفی
PASSWORD_LENGTH = 12      # طول رمز عبور تصادفی

# ---------- توابع کمکی ----------
def generate_random_string(length, chars=string.ascii_lowercase + string.digits):
    """تولید رشته تصادفی برای نام کاربری یا رمز عبور"""
    return ''.join(random.choices(chars, k=length))

def extract_code(text):
    """
    جستجوی کد تأیید ۴ تا ۸ رقمی در متن ایمیل
    از چندین الگوی رایج استفاده می‌کند
    """
    if not text:
        return None

    patterns = [
        r'\b(\d{4,8})\b',                      # کد ۴ تا ۸ رقمی خالی
        r'code[:\s]+(\d{4,8})',                # "code: 123456"
        r'otp[:\s]+(\d{4,8})',                 # "OTP: 123456"
        r'verification[:\s]+(\d{4,8})',        # "verification: 123456"
        r'confirm[:\s]+(\d{4,8})',             # "confirm: 123456"
        r'کد[:\s]+(\d{4,8})',                  # "کد: 123456"
        r'تأیید[:\s]+(\d{4,8})',               # "تأیید: 123456"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def clean_text_from_html(html_content):
    """تبدیل HTML به متن ساده (حذف تگ‌ها)"""
    if isinstance(html_content, list):
        html_content = ' '.join(html_content)
    # حذف تگ‌های HTML
    text = re.sub(r'<[^>]+>', ' ', html_content)
    # حذف فاصله‌های اضافی
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ---------- بدنه اصلی ----------
def main():
    print("🚀 راه‌اندازی ایمیل موقت با mail.tm ...\n")

    # ---------- 1. دریافت دامنه‌های موجود ----------
    try:
        resp = requests.get("https://api.mail.tm/domains", timeout=10)
        resp.raise_for_status()
        domains = resp.json().get("hydra:member", [])
        if not domains:
            print("❌ هیچ دامنه فعالی از mail.tm دریافت نشد.")
            sys.exit(1)
        # اولین دامنه را انتخاب می‌کنیم
        domain = domains[0]["domain"]
        print(f"✅ دامنه انتخاب شد: @{domain}")
    except Exception as e:
        print(f"❌ خطا در دریافت دامنه‌ها: {e}")
        sys.exit(1)

    # ---------- 2. ساخت حساب کاربری تصادفی ----------
    username = generate_random_string(USERNAME_LENGTH)
    password = generate_random_string(PASSWORD_LENGTH, string.ascii_letters + string.digits)
    email_address = f"{username}@{domain}"

    account_payload = {
        "address": email_address,
        "password": password
    }

    try:
        resp = requests.post("https://api.mail.tm/accounts", json=account_payload, timeout=10)
        # اگر حساب تکراری باشد، خطا می‌دهد (احتمال بسیار کم)
        if resp.status_code == 422:
            # دوباره با نام کاربری جدید امتحان می‌کنیم
            username = generate_random_string(USERNAME_LENGTH + 2)
            email_address = f"{username}@{domain}"
            account_payload["address"] = email_address
            resp = requests.post("https://api.mail.tm/accounts", json=account_payload, timeout=10)
        resp.raise_for_status()
        print(f"📧 ایمیل موقت ساخته شد: {email_address}")
    except Exception as e:
        print(f"❌ خطا در ساخت حساب: {e}")
        sys.exit(1)

    # ---------- 3. دریافت توکن احراز هویت ----------
    try:
        token_resp = requests.post("https://api.mail.tm/token", json=account_payload, timeout=10)
        token_resp.raise_for_status()
        token = token_resp.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("🔐 توکن امنیتی دریافت شد.\n")
    except Exception as e:
        print(f"❌ خطا در دریافت توکن: {e}")
        sys.exit(1)

    # ---------- 4. نمایش راهنما و انتظار برای ایمیل ----------
    print("⏳ منتظر دریافت ایمیل حاوی کد تأیید...")
    print("📌 لطفاً آدرس ایمیل زیر را در سایت/اپلیکیشن مورد نظر وارد کنید")
    print("   و درخواست ارسال کد تأیید را بزنید.\n")
    print(f"👉 {email_address}\n")
    print(f"⏱️  حداکثر زمان انتظار: {WAIT_TIMEOUT} ثانیه\n")

    start_time = time.time()
    found_code = None
    check_count = 0

    while time.time() - start_time < WAIT_TIMEOUT:
        check_count += 1
        try:
            # دریافت لیست پیام‌ها
            msg_resp = requests.get("https://api.mail.tm/messages", headers=headers, timeout=10)
            msg_resp.raise_for_status()
            messages = msg_resp.json().get("hydra:member", [])

            if messages:
                # ایمیل دریافت شده است
                latest_msg = messages[0]  # جدیدترین ایمیل
                msg_id = latest_msg["id"]
                subject = latest_msg.get("subject", "(بدون موضوع)")
                from_addr = latest_msg.get("from", {}).get("address", "ناشناس")

                # دریافت محتوای کامل ایمیل
                detail_resp = requests.get(f"https://api.mail.tm/messages/{msg_id}", headers=headers, timeout=10)
                detail_resp.raise_for_status()
                detail = detail_resp.json()

                # استخراج متن
                body_text = ""
                if detail.get("text"):
                    body_text = detail["text"]
                elif detail.get("html"):
                    body_text = clean_text_from_html(detail["html"])

                print(f"\n📨 ایمیل جدید دریافت شد (بررسی #{check_count})")
                print(f"   از: {from_addr}")
                print(f"   موضوع: {subject}")

                # جستجوی کد تأیید
                code = extract_code(body_text)
                if code:
                    found_code = code
                    print(f"   ✅ کد تأیید پیدا شد: {found_code}")
                    # حذف ایمیل برای تمیزی (اختیاری)
                    requests.delete(f"https://api.mail.tm/messages/{msg_id}", headers=headers)
                    break
                else:
                    print("   ⚠️ کد تأییدی در این ایمیل یافت نشد. منتظر ایمیل بعدی...")
                    # حذف ایمیل بی‌فایده
                    requests.delete(f"https://api.mail.tm/messages/{msg_id}", headers=headers)
            else:
                # هنوز ایمیلی نیامده
                if check_count % (60 // POLL_INTERVAL) == 0:
                    # هر دقیقه یک بار وضعیت را چاپ کن
                    elapsed = int(time.time() - start_time)
                    print(f"⏲️  هنوز ایمیلی دریافت نشده ( {elapsed} ثانیه گذشته )")
                else:
                    print(".", end="", flush=True)

            time.sleep(POLL_INTERVAL)

        except requests.exceptions.RequestException as e:
            print(f"\n⚠️ خطای شبکه در بررسی صندوق: {e}")
            time.sleep(POLL_INTERVAL * 2)  # کمی بیشتر صبر کن
        except Exception as e:
            print(f"\n⚠️ خطای پیش‌بینی‌نشده: {e}")
            time.sleep(POLL_INTERVAL)

    # ---------- 5. نتیجه نهایی ----------
    print("\n" + "=" * 50)
    if found_code:
        print(f"✅ عملیات با موفقیت به پایان رسید.")
        print(f"📧 ایمیل: {email_address}")
        print(f"🔢 کد تأیید: {found_code}")

        # ذخیره خروجی برای استفاده در مراحل بعدی گیت‌هاب (اختیاری)
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"email={email_address}\n")
                f.write(f"code={found_code}\n")
        sys.exit(0)
    else:
        print(f"❌ در مدت {WAIT_TIMEOUT} ثانیه هیچ کد تأییدی دریافت نشد.")
        print(f"   ایمیل ساخته شده: {email_address}")
        sys.exit(1)

if __name__ == "__main__":
    main()
