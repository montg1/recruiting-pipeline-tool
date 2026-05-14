from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import os
import re

# --- ตั้งค่า ---
LINKEDIN_EMAIL = ""
LINKEDIN_PASSWORD = ""
TARGET_PROFILE = "https://linkedin.com/in/williamhgates/"

# เซฟ HTML ไว้ debug (จะบันทึกไว้ข้างๆ ไฟล์นี้)
SAVE_HTML_FOR_DEBUG = True


def parse_profile_html(html_content):
    """
    Parser สำหรับ LinkedIn 2025+ ที่ใช้ obfuscated class names
    ใช้ text content, aria-label, tag structure แทน CSS class
    """
    soup = BeautifulSoup(html_content, 'lxml')
    profile = {
        "Name": "Not Found",
        "Headline": "Not Found",
        "Location": "Not Found",
        "About": "Not Found",
        "Company": "Not Found",
        "Education": "Not Found",
        "Connections": "Not Found",
        "OpenToWork": "Not Found",
    }

    # === 1. ดึงชื่อจาก <title> tag (วิธีที่เชื่อถือได้ที่สุด) ===
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        # LinkedIn title format: "Name | LinkedIn"
        if "|" in title_text:
            profile["Name"] = title_text.split("|")[0].strip()

    # === 2. ดึงชื่อจาก h2 ใน topcard section (fallback) ===
    if profile["Name"] == "Not Found":
        # ลองหา h2 ที่ตรงกับชื่อ (LinkedIn ย้ายจาก h1 ไปเป็น h2 แล้ว)
        for h2 in soup.find_all("h2"):
            text = h2.get_text(strip=True)
            # กรอง h2 ที่ไม่ใช่ชื่อคนออก
            if text and text not in [
                "0 notifications", "Suggested for you", "Analytics",
                "Activity", "Profile language", "Public profile & URL"
            ] and len(text) < 60 and not text.startswith("Show"):
                profile["Name"] = text
                break

    # === 3. ดึง Headline ===
    # Headline มักจะอยู่ใน <p> tag ที่มี class _8bce2fa5 (แต่เราไม่ใช้ class)
    # ค้นหาจาก topcard section: หลังชื่อจะมี headline
    # ลองหาจาก div ที่มี aria-label ชื่อคน
    name_div = soup.find("div", attrs={"aria-label": re.compile(r"Oatsada|" + re.escape(profile["Name"].split()[0]) if profile["Name"] != "Not Found" else ".*")})
    
    # หาจาก <p> tags ใน topcard ที่มีข้อความภาษาไทยเกี่ยวกับอาชีพ/สถานะ
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        # Headline มักเป็นข้อความสั้นๆ ที่อธิบายตำแหน่ง
        if text and ("นักศึกษา" in text or "Student" in text or "Engineer" in text or 
                     "Developer" in text or "Manager" in text or "at " in text or "ที่ " in text):
            # ตรวจสอบว่าไม่ใช่ส่วนอื่น
            parent_section = p.find_parent("section")
            if parent_section and parent_section.get("aria-label") in [None, "Primary content"]:
                profile["Headline"] = text
                break

    # === 4. ดึง Location ===
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if text and ("Thailand" in text or "Bangkok" in text or "Ratchathani" in text or 
                     ", " in text) and len(text) < 80:
            # ตรวจว่าเป็น location จริง ไม่ใช่ข้อความอื่น
            if not any(skip in text for skip in ["profile", "http", "linkedin", "Show", "followers", 
                                                   "connections", "views", "impressions", "appearances",
                                                   "Contact", "Open to", "work"]):
                profile["Location"] = text
                break

    # === 5. ดึง Company & Education จาก topcard ===
    # LinkedIn แสดง company + school ใน topcard เป็น text "Company · School"
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if "·" in text and len(text) < 200:
            parts = [part.strip() for part in text.split("·")]
            if len(parts) >= 2:
                profile["Company"] = parts[0]
                profile["Education"] = parts[1]
                break

    # === 6. ดึง Company จาก span ที่มี text ของ company name ===
    if profile["Company"] == "Not Found":
        for span in soup.find_all("span"):
            text = span.get_text(strip=True)
            if text and ("Co.,LTD" in text or "Company" in text or "Corp" in text or "Inc" in text):
                profile["Company"] = text
                break

    # === 7. ดึงจำนวน Connections ===
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if "connections" in text.lower() and len(text) < 30:
            profile["Connections"] = text
            break

    # === 8. ดึง Open to Work info ===
    for p in soup.find_all("p"):
        text = p.get_text(strip=True)
        if "Open to work" in text:
            profile["OpenToWork"] = text
            break
    
    # ดึง Open to Work details (location + work type)
    for span in soup.find_all("span"):
        text = span.get_text(strip=True)
        if "On-site" in text or "Remote" in text or "Hybrid" in text:
            profile["OpenToWork"] = text
            break

    # === 9. ดึง Experience sections (ถ้ามี) ===
    # LinkedIn 2025 ใช้ section tag พร้อม componentkey
    experience_data = []
    for section in soup.find_all("section"):
        # หา section ที่มี h2 "Experience" หรือ "ประสบการณ์"
        h2 = section.find("h2")
        if h2:
            h2_text = h2.get_text(strip=True).lower()
            if "experience" in h2_text or "ประสบการณ์" in h2_text:
                # ดึง text จาก span ที่แสดงผลจริง (aria-hidden="true") เพื่อเก็บข้อมูลทั้งหมด (บริษัท, ตำแหน่ง, วันที่)
                spans = section.find_all("span", attrs={"aria-hidden": "true"})
                if not spans:
                    spans = section.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and len(text) > 1:
                        experience_data.append(text)
                        
    # Fallback: หาจากลิงก์ /position/ (สำหรับโพรไฟล์ของตัวเอง) หรือหาโครงสร้าง ul li
    if not experience_data:
        for a_tag in soup.find_all("a", href=re.compile(r"/position/|/details/experience/")):
            div = a_tag.find("div")
            if div:
                for p in div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 1:
                        experience_data.append(text)

    if experience_data:
        # ลบข้อมูลที่ซ้ำกัน และกรองข้อความขยะ
        unique_exp = []
        for exp in experience_data:
            if exp not in unique_exp and not any(skip in exp for skip in ["Show all", "ดูทั้งหมด", "ประสบการณ์", "Experience"]):
                unique_exp.append(exp)
        profile["WorkExperience"] = unique_exp

    # === 10. ดึง Education sections (ถ้ามี) ===
    education_data = []
    for section in soup.find_all("section"):
        h2 = section.find("h2")
        if h2:
            h2_text = h2.get_text(strip=True).lower()
            if "education" in h2_text or "การศึกษา" in h2_text:
                spans = section.find_all("span", attrs={"aria-hidden": "true"})
                if not spans:
                    spans = section.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and len(text) > 1:
                        education_data.append(text)
                        
    # Fallback: หาจากลิงก์ /education/ 
    if not education_data:
        for a_tag in soup.find_all("a", href=re.compile(r"/education/|/details/education/")):
            div = a_tag.find("div")
            if div:
                for p in div.find_all("p"):
                    text = p.get_text(strip=True)
                    if text and len(text) > 1:
                        education_data.append(text)

    if education_data:
        unique_edu = []
        for edu in education_data:
            if edu not in unique_edu and not any(skip in edu for skip in ["Show all", "ดูทั้งหมด", "การศึกษา", "Education"]):
                unique_edu.append(edu)
        profile["EducationDetails"] = unique_edu

    # === 11. ดึง Skills sections (ถ้ามี) ===
    skills_data = []
    for section in soup.find_all("section"):
        h2 = section.find("h2")
        if h2:
            h2_text = h2.get_text(strip=True).lower()
            if "skills" in h2_text or "ทักษะ" in h2_text:
                spans = section.find_all("span", attrs={"aria-hidden": "true"})
                if not spans:
                    spans = section.find_all("span")
                for span in spans:
                    text = span.get_text(strip=True)
                    if text and len(text) > 1:
                        skills_data.append(text)

    if skills_data:
        unique_skills = []
        for skill in skills_data:
            if skill not in unique_skills and not any(skip in skill for skip in ["Show all", "ดูทั้งหมด", "ทักษะ", "Skills", "Endorsed", "ได้รับการรับรอง"]):
                unique_skills.append(skill)
        profile["Skills"] = unique_skills

    return profile


def scrape_local():
    print("🚀 กำลังเปิด Google Chrome...")
    options = webdriver.ChromeOptions()
    options.add_argument('--start-maximized')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_argument('--lang=en-US')
    # User-Agent ปกติเพื่อไม่ให้ LinkedIn สงสัย
    options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    # ซ่อนแจ้งเตือน Chrome ว่าโดนคุมด้วยบอท (ทำให้เนียนขึ้น)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # ลบ navigator.webdriver flag เพื่อ bypass detection
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })

    try:
        print("🔑 เปิดหน้า Login...")
        driver.get("https://www.linkedin.com/login")
        
        # รอจนกว่าฟิลด์อีเมลจะโหลดขึ้นมา (เผื่อเน็ตช้า) และรองรับฟอร์ม 2 รูปแบบของ LinkedIn
        try:
            print("⏳ รอหน้า Login โหลด...")
            email_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            password_field = driver.find_element(By.ID, "password")
        except:
            # กรณี LinkedIn สุ่มหน้า Login อีกรูปแบบมาให้
            email_field = WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.ID, "session_key"))
            )
            password_field = driver.find_element(By.ID, "session_password")

        email_field.send_keys(LINKEDIN_EMAIL)
        password_field.send_keys(LINKEDIN_PASSWORD)
        
        try:
            driver.find_element(By.XPATH, "//button[@type='submit']").click()
        except:
            driver.find_element(By.CLASS_NAME, "sign-in-form__submit-button").click()

        # รอให้หน้า Feed โหลดเสร็จ หรือรอให้ผู้ใช้แก้ CAPTCHA
        input("🛑 [รอการยืนยัน]: รอให้โหลดหน้าแรกเสร็จ / แก้ CAPTCHA ให้เสร็จ แล้วกด Enter ที่จอ Terminal...")

        print(f"🔗 เข้าสู่หน้าโปรไฟล์: {TARGET_PROFILE}")
        driver.get(TARGET_PROFILE)

        # === รอจนกว่าหน้าจะโหลดเสร็จจริง ===
        print("⏳ รอให้หน้าโปรไฟล์โหลดเสร็จ...")
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "h2"))
            )
        except Exception:
            print("⚠️ ไม่พบ h2 ภายใน 15 วิ - อาจถูก block หรือหน้าโหลดไม่สมบูรณ์")

        time.sleep(3)  # รอเพิ่มเผื่อ JS render

        print("🔄 กำลังไถหน้าจอเพื่อดึงข้อมูลเชิงลึก (Lazy Load) โดยจำลองการกดคีย์บอร์ด...")
        body = driver.find_element(By.TAG_NAME, "body")
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        while True:
            # กด Page Down หลายๆ ครั้งเพื่อค่อยๆ เลื่อนลงมา
            for _ in range(4):
                body.send_keys(Keys.PAGE_DOWN)
                time.sleep(0.6)  # รอแป๊บเดียวในแต่ละสเตปการเลื่อน
            
            # เมื่อเลื่อนเสร็จแล้ว ให้รอหน้าใหม่โหลด
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                # ลองกด END เพื่อให้แน่ใจว่าเลื่อนสุดจริงๆ
                body.send_keys(Keys.END)
                time.sleep(2)
                new_height = driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    break # โหลดหมดแล้ว ออกจาก loop
            last_height = new_height

        # เลื่อนกลับขึ้นไปบนสุดเพื่อให้แน่ใจว่า DOM ครบ
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(3)

        print("🧠 กำลังแกะข้อมูล HTML...")
        raw_html = driver.page_source

        # บันทึก HTML ไว้ debug
        if SAVE_HTML_FOR_DEBUG:
            debug_path = os.path.join(os.path.dirname(__file__), "linkedin_debug.html")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(raw_html)
            print(f"💾 บันทึก HTML ไว้ที่: {debug_path}")

        profile_data = parse_profile_html(raw_html)

        # === แสดงผลลัพธ์ ===
        print("\n" + "=" * 60)
        print("✅ ดึงข้อมูลสำเร็จ! ผลลัพธ์ (JSON):")
        print("=" * 60)
        print(json.dumps(profile_data, indent=2, ensure_ascii=False))

        # แจ้งเตือนถ้าข้อมูลหลักหายไป
        not_found_count = sum(1 for v in profile_data.values() if v == "Not Found")
        if not_found_count > 0:
            print(f"\n⚠️ มี {not_found_count} ฟิลด์ที่ยังไม่พบข้อมูล")
        else:
            print("\n🎉 ดึงข้อมูลครบทุกฟิลด์!")

    except Exception as e:
        print(f"\n❌ เกิดข้อผิดพลาด: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 ปิดเบราว์เซอร์...")
        driver.quit()


if __name__ == "__main__":
    scrape_local()