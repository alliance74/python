import pandas as pd
from selenium.webdriver.common.by import By
import time
import random
import re
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 1. LOAD DATA
df = pd.read_csv("RCA_Books_Final.csv")
target_col = 'Description'
df = df.dropna(subset=[target_col])

# 2. DRIVER SETUP (Standard Selenium to avoid download hangs)
options = webdriver.ChromeOptions()
# Adding arguments to make it slightly less obvious
options.add_argument(('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                      'AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/120.0.0.0 Safari/537.36'))
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option('useAutomationExtension', False)

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def get_book_metadata(title):
    try:
        # Human-like delay: randomized between 3 and 6 seconds
        time.sleep(random.uniform(3.0, 6.0))
        
        # 1. Search for the book
        driver.get(f"https://www.google.com/search?tbm=bks&q={title}")
        
        # Manual CAPTCHA Check
        if "unusual traffic" in driver.page_source:
            print(f"!!! Google blocked us on: {title[:30]}")
            print("Please solve the CAPTCHA in the browser window now...")
            while "unusual traffic" in driver.page_source:
                time.sleep(3)

        # 2. Click on the first result to go to the Edition Page
        try:
            # First book result usually in h3 or a specific wrapper
            first_book = driver.find_element(By.CSS_SELECTOR, "a > h3")
            # Navigate to the book detail page
            driver.execute_script("arguments[0].click();", first_book)
            time.sleep(3) # Wait for page load
        except:
            print(f"   > No book link found for: {title[:30]}")
            return "Not Found", "Not Found", "N/A"

        # 3. Scroll Down to "Bibliographic information"
        # We scroll to the bottom to trigger lazy loading if needed, then scan
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)

        # 4. Extract Data from Bibliographic Information Table
        # Google Books details usually have rows like "Title: ...", "Author: ...", "ISBN: ..."
        # These are often in a table with class 'G3P7Ve' or generic rows
        page_source = driver.page_source
        
        author = "Unknown Author"
        publisher = "Unknown Publisher"
        isbn = "N/A"

        # --- EXTRACT AUTHOR ---
        # Try to find a specific row or use the regex fallback
        try:
            # Common pattern for author on detail page
            # Look for "Author" label
            rows = driver.find_elements(By.XPATH, "//span[contains(text(), 'Author')]/.. | //div[contains(text(), 'Author')]/..")
            for row in rows:
                if "Author" in row.text:
                    author = row.text.replace("Author", "").replace(":", "").strip()
                    break
        except: pass

        # --- EXTRACT PUBLISHER ---
        try:
            # Look for "Publisher" label
            rows = driver.find_elements(By.XPATH, "//span[contains(text(), 'Publisher')]/.. | //div[contains(text(), 'Publisher')]/..")
            for row in rows:
                if "Publisher" in row.text:
                    publisher = row.text.replace("Publisher", "").replace(":", "").strip()
                    break
        except: pass

        # --- EXTRACT ISBN ---
        isbn_match = re.search(r'978[-0-9]{10,14}', page_source)
        if isbn_match:
            isbn = isbn_match.group(0).replace('-', '').replace(' ', '')
        else:
            # Try finding the ISBN row in the table
            try:
                rows = driver.find_elements(By.XPATH, "//span[contains(text(), 'ISBN')]/.. | //div[contains(text(), 'ISBN')]/..")
                for row in rows:
                    if "ISBN" in row.text:
                         # Extract the number from the text
                         nums = re.findall(r'\d+', row.text)
                         # join to see if it makes a valid ISBN likely
                         candidate = "".join(nums)
                         if len(candidate) >= 10:
                             isbn = candidate
                             break
            except: pass
        
        return author, publisher, isbn
    except Exception as e:
        print(f"Error scraping {title}: {e}")
        return "Error", "Error", "N/A"

# 3. RUN THE SCRAPER (With Resume & Incremental Save)
output_json = "final_results_by_pro_alli.json"
output_csv = "RCA_Books_Stealth_Final.csv"

# Load existing state if available to RESUME
stylesheet = {}
scraped_titles = set()

if os.path.exists(output_json):
    try:
        with open(output_json, "r") as f:
            stylesheet = json.load(f)
        # Extract titles to identify what's already done
        for key, val in stylesheet.items():
            scraped_titles.add(val['title'])
        print(f"RESUMING... Found {len(stylesheet)} books already scraped.")
    except Exception as e:
        print(f"Warning: Could not load existing file ({e}). Starting fresh.")

# Check if CSV exists for header management
csv_headers_written = os.path.exists(output_csv)

for index, row in df.iterrows():
    title = row[target_col]
    
    # RESUME CHECK
    if title in scraped_titles:
        print(f"[{index+1}/{len(df)}] Skipping: {title} (Already Scraped)")
        continue

    print(f"[{index+1}/{len(df)}] Scraping: {title[:50]}...")
    
    auth, pub, code = get_book_metadata(title)
    
    # Check if we actually found something
    status = "SUCCESS" if code != "N/A" and auth != "Not Found" else "PARTIAL/FAIL"
    
    # 1. Update JSON Data (The "Object" Store)
    slug = re.sub(r'\W+', '_', str(title).lower())[:35]
    stylesheet[slug] = {
        "title": title,
        "author": auth,
        "publisher": pub,
        "isbn": str(code).split('.')[0],
        "inventory": {
            "qty": row.get('Quantity', 0),
            "price": row.get('Unit price', 0),
            "total": row.get('Total Price p', 0)
        }
    }
    
    # 2. Append to CSV Data
    entry = row.to_dict()
    entry['Author'] = auth
    entry['Publisher'] = pub
    entry['ISBN'] = str(code).split('.')[0]
    
    # --- INCREMENTAL SAVE ---
    # Save JSON immediately
    with open(output_json, "w") as f:
        json.dump(stylesheet, f, indent=4)
        
    # Append to CSV immediately
    pd.DataFrame([entry]).to_csv(output_csv, mode='a', header=not csv_headers_written, index=False)
    csv_headers_written = True # Headers written after first write/exist check
    
    print(f"   > [{status}] Saved. (A: {auth} | P: {pub} | I: {code})")

driver.quit()
print(f"\nSuccess! Completed scraping. Data saved to:\n1. {output_json}\n2. {output_csv}")