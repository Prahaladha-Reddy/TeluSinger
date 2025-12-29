from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import re

def setup_driver():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0")
    return webdriver.Chrome(options=opts)

def main():
    url = "https://www.jiosaavn.com/artist/sirivennela-seetharama-sastry-songs/u-vLZvgDCPM_"
    
    print("Starting browser...")
    driver = setup_driver()
    
    try:
        driver.get(url)
        time.sleep(3)
        
        try:
            driver.execute_script("""
                document.querySelectorAll('[class*="modal"], [class*="popup"], [class*="overlay"]')
                    .forEach(el => el.remove());
            """)
        except:
            pass
        
        clicks = 0
        while clicks < 100:  
            try:
                btn = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, 
                        "//button[contains(@class, 'c-btn') and contains(., 'Load more')]"))
                )
                
                driver.execute_script(
                    "arguments[0].scrollIntoView({block: 'center'});", btn)
                time.sleep(0.5)
                
                driver.execute_script("arguments[0].click();", btn)
                clicks += 1
                print(f"Clicked Load more ({clicks})...")
                time.sleep(1.5)
                
            except Exception as e:
                print(f"No more Load more button: {type(e).__name__}")
                break
        
        print(f"\nClicked {clicks} times. Extracting songs...")
        
        songs = []
        rows = driver.find_elements(By.CSS_SELECTOR, "article.o-snippet, figure.c-snippet")
        
        if not rows:
            rows = driver.find_elements(By.XPATH, "//a[contains(@href, '/song/')]/..")
        
        print(f"Found {len(rows)} song elements")
        
        for row in rows:
            try:
                html = row.get_attribute("innerHTML")
                
                song_match = re.search(r'href="/song/[^"]+">([^<]+)</a>', html)
                song_name = song_match.group(1).strip() if song_match else ""
                
                album_match = re.search(r'href="/album/[^"]+">([^<]+)</a>', html)
                album = album_match.group(1).strip() if album_match else ""
                
                artist_matches = re.findall(r'href="/artist/[^"]+">([^<]+)</a>', html)
                singers = ", ".join(artist_matches) if artist_matches else ""
                
                if song_name:
                    songs.append({
                        "song_name": song_name,
                        "movie_album": album,
                        "singers": singers
                    })
            except Exception as e:
                continue
        
        if len(songs) < 50:
            print("Trying alternative extraction...")
            page_html = driver.page_source
            
            pattern = r'\[([^\]]+)\]\(/song/([^)]+)\)[^\[]*\[([^\]]+)\][^\[]*\[([^\]]+)\]'
            matches = re.findall(pattern, page_html)
            
            for m in matches:
                song_name = m[0].strip()
                if song_name and not any(s["song_name"] == song_name for s in songs):
                    songs.append({
                        "song_name": song_name,
                        "movie_album": m[3].strip() if len(m) > 3 else "",
                        "singers": m[2].strip() if len(m) > 2 else ""
                    })
        
        seen = set()
        unique = []
        for s in songs:
            key = s["song_name"].lower()
            if key and key not in seen:
                seen.add(key)
                unique.append(s)
        
        print(f"\nExtracted {len(unique)} unique songs")
        
        if unique:
            with open("sirivennela_songs.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["song_name", "movie_album", "singers"])
                writer.writeheader()
                writer.writerows(unique)
            print(f" Saved to sirivennela_songs.csv")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    main()