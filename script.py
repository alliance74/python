import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import json

# 1. LOAD DATA
df = pd.read_csv("RCA_Books_Final.csv") # Using your generated file
target_col = 'Description'
df = df.dropna(subset=[target_col])

# 2. SELENIUM SETUP
options = webdriver.ChromeOptions()
options.add_experimental_option('excludeSwitches', ['enable-logging'])
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_book_info(title):
    try:
        driver.get(f"https://www.google.com/search?tbm=bks&q={title}")
        time.sleep(2)
        
        # FIXED AUTHOR SELECTOR
        # Google Books often places Author in a specific <span> or <a> within the metadata div
        try:
            # We look for the metadata container and split by '-' 
            # as Google usually shows "Author - Year - Pages"
            meta_text = driver.find_element(By.CSS_SELECTOR, ".N97eTe").text
            author = meta_text.split(' - ')[0] 
        except:
            author = "Unknown Author"

        # FIXED ISBN (REGEX)
        isbn_match = re.search(r'978[-0-9]{10,14}', driver.page_source)
        isbn = isbn_match.group(0).replace('-', '') if isbn_match else "N/A"
        
        return author, isbn
    except:
        return "Error", "N/A"

# 3. RUN SCRAPING
authors, isbns = [], []
for title in df[target_col]:
    print(f"Scraping: {title}...")
    auth, code = scrape_book_info(title)
    authors.append(auth)
    isbns.append(code)

df['Author'] = authors
df['ISBN'] = isbns

# 4. EXPORT AS "STYLESHEET" (JSON FORMAT)
# Converting the table into a key-value pair structure for easy React mapping
stylesheet_data = {}
for _, row in df.iterrows():
    # Create a unique key based on the description (removed spaces)
    key = re.sub(r'\W+', '', str(row['Description']))[:30].lower()
    stylesheet_data[key] = {
        "title": row['Description'],
        "author": row['Author'],
        "isbn": row['ISBN'],
        "price": row['Total Price p'],
        "quantity": row['Quantity']
    }

with open('book_styles.json', 'w') as f:
    json.dump(stylesheet_data, f, indent=4)

driver.quit()
print("\nSuccess! Generated 'book_styles.json' for your app.")