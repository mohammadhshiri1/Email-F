#!/usr/bin/env python3
"""
ایمیل موقت با Guerrilla Mail – بدون ثبت‌نام، بدون توکن
"""

import os
import sys
import time
import re
import random
import string
import requests

# ---------- تنظیمات ----------
WAIT_TIMEOUT = 180
POLL_INTERVAL = 5
USERNAME_LENGTH = 10

def generate_random_string(length):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def extract_code(text):
    if not text:
        return None
    patterns = [
        r'\b(\d{4,8})\b',
        r'code[:\s]+(\d{4,8})',
        r'otp[:\s]+(\d{4,8})',
        r'verification[:\s]+(\d{4,8})',
        r'کد[:\s]+(\d{4,8})',
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def main():
    print("🚀 راه‌اندازی ایمیل موقت با Guerrilla Mail\n")

    # ساخت ایمیل تصادفی
    username = generate_random_string(USERNAME_LENGTH)
    # دامنه‌های رایج Guerrilla Mail
    domains = ["guerrillamail.com", "sharklasers.com", "grr.la"]
    domain = random.choice(domains)
    email_address = f"{username}@{domain}"

    # فعال‌سازی صندوق با یک درخواست ساده
    session = requests.Session()
    params = {
        "f": "set_email_user",
        "email_user": username,
        "domain": domain,
    }
    try:
        init_resp = session.get("https://www.guerrillamail.com/ajax.php", params=params, timeout=10)
        init_resp.raise_for_status()
        data = init_resp.json()
        if not data.get("email_addr"):
            print("❌ خطا در ساخت ایمیل موقت.")
            sys.exit(1)
        print(f"📧 ایمیل موقت ساخته شد: {email_address}")
    except Exception as e:
        print(f"❌ خطا در راه‌اندازی: {e}")
        sys.exit(1)

    # شناسه صندوق (sid_token) برای درخواست‌های بعدی
    sid_token = data.get("sid_token")

    print("⏳ منتظر دریافت ایمیل حاوی کد تأیید...")
    print("📌 لطفاً آدرس ایمیل زیر را در سایت/اپلیکیشن وارد کنید:")
    print(f"👉 {email_address}\n")
    print(f"⏱️  حداکثر زمان انتظار: {WAIT_TIMEOUT} ثانیه\n")

    start_time = time.time()
    found_code = None
    last_seen_id = 0
    check_count = 0

    while time.time() - start_time < WAIT_TIMEOUT:
        check_count += 1
        try:
            # چک کردن ایمیل‌های جدید
            fetch_params = {
                "f": "fetch_email",
                "sid_token": sid_token,
                "seq": last_seen_id,
            }
            fetch_resp = session.get("https://www.guerrillamail.com/ajax.php", params=fetch_params, timeout=10)
            fetch_resp.raise_for_status()
            result = fetch_resp.json()

            if result.get("list"):
                # ایمیل جدید داریم
                for mail in result["list"]:
                    mail_id = mail["mail_id"]
                    subject = mail.get("mail_subject", "(بدون موضوع)")
                    from_addr = mail.get("mail_from", "ناشناس")
                    mail_body = mail.get("mail_body", "")

                    # حذف تگ‌های HTML از بدنه
                    body_text = re.sub(r'<[^>]+>', ' ', mail_body)
                    body_text = re.sub(r'\s+', ' ', body_text).strip()

                    print(f"\n📨 ایمیل دریافت شد (بررسی #{check_count})")
                    print(f"   از: {from_addr}")
                    print(f"   موضوع: {subject}")

                    code = extract_code(body_text)
                    if code:
                        found_code = code
                        print(f"   ✅ کد تأیید: {found_code}")
                        break
                    else:
                        print("   ⚠️ کدی یافت نشد. منتظر ایمیل بعدی...")
                        last_seen_id = mail_id  # جلوگیری از خواندن مجدد همان ایمیل

                if found_code:
                    break
            else:
                if check_count % (60 // POLL_INTERVAL) == 0:
                    elapsed = int(time.time() - start_time)
                    print(f"⏲️  هنوز ایمیلی نیامده ( {elapsed} ثانیه )")
                else:
                    print(".", end="", flush=True)

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            print(f"\n⚠️ خطا: {e}")
            time.sleep(POLL_INTERVAL * 2)

    print("\n" + "=" * 50)
    if found_code:
        print(f"✅ موفقیت!")
        print(f"📧 ایمیل: {email_address}")
        print(f"🔢 کد: {found_code}")
        if "GITHUB_OUTPUT" in os.environ:
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"email={email_address}\n")
                f.write(f"code={found_code}\n")
        sys.exit(0)
    else:
        print(f"❌ کدی دریافت نشد (زمان: {WAIT_TIMEOUT} ثانیه).")
        print(f"   ایمیل ساخته‌شده: {email_address}")
        sys.exit(1)

if __name__ == "__main__":
    main()
