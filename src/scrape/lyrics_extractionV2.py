
import csv
import time
import re
import logging
import random
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import quote_plus
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

OUTPUT_DIR = "lyrics_stealth_v13"
HEADLESS = False           
MIN_TELUGU_CHARS = 30       
MAX_RESULTS_TO_CHECK = 7    

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

class StealthDeepScraper:
    def __init__(self):
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.driver = self._setup_driver()

    def _setup_driver(self):
        options = uc.ChromeOptions()
        if HEADLESS:
            options.add_argument('--headless')
        driver = uc.Chrome(options=options)
        return driver

    def close(self):
        self.driver.quit()

    def count_telugu_chars(self, text):
        return len(re.findall(r'[\u0C00-\u0C7F]', text))

    def clean_text(self, text):
        if not text: return ""
        lines = [line.strip() for line in text.split('\n')]
        cleaned = []
        for line in lines:
            if not line: continue
            low = line.lower()
            if any(x in low for x in ['share', 'comment', 'whatsapp', 'search', 'home', 'click here', 'advertisement']):
                continue
            cleaned.append(line)
        return '\n'.join(cleaned)

    def process_song(self, song, movie):
        try:
            query = f"lyricstape.com {song} {movie} lyrics"
            encoded_query = quote_plus(query)
            ddg_url = f"https://duckduckgo.com/?q={encoded_query}&t=h_&ia=web"
            
            self.driver.get(ddg_url)
            
            wait = WebDriverWait(self.driver, 5)
            
            try:
                result_elements = wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "li[data-layout='organic'] h2 a")))
                
                candidate_urls = []
                for elem in result_elements[:MAX_RESULTS_TO_CHECK]:
                    url = elem.get_attribute("href")
                    if url:
                        candidate_urls.append(url)

                if not candidate_urls:
                    return False, "No search results found"

            except Exception as e:
                return False, "Search results selector failed"

            target_url = None
            
            for url in candidate_urls:
                if "lyricstape.com" in url:
                    target_url = url
                    break
            
            if not target_url:
                return False, f"Lyricstape not found in top {MAX_RESULTS_TO_CHECK} results"


            self.driver.get(target_url)
            
            time.sleep(3)
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            content = self._extract_from_soup(soup)
            
            if content:
                return True, content
            else:
                return False, "Page loaded, but no Telugu text found"

        except Exception as e:
            return False, f"Error: {e}"

    def _extract_from_soup(self, soup):
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'form', 'noscript']):
            tag.decompose()

        best_text = ""
        max_score = 0
        
        for elem in soup.find_all(['div', 'article', 'p', 'span']):
            text = elem.get_text(separator='\n')
            score = self.count_telugu_chars(text)
            
            if score > max_score:
                max_score = score
                best_text = text
        
        if max_score >= MIN_TELUGU_CHARS:
            return self.clean_text(best_text)
        return None

    def save_file(self, song, movie, content):
        clean_movie = re.sub(r'[^\w\-_]', '', movie.replace(' ', '_'))
        clean_song = re.sub(r'[^\w\-_]', '', song.replace(' ', '_'))
        
        folder = self.output_dir / clean_movie
        folder.mkdir(exist_ok=True)
        
        path = folder / f"{clean_song}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Song: {song}\nMovie: {movie}\nSource: Lyricstape (DDG-DeepScan)\n\n{content}")

    def run(self, csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            songs = list(csv.DictReader(f))
            
        print(f"--- Deep Scan Scraper (Top {MAX_RESULTS_TO_CHECK}) Started ---")
        
        stats = {'found': 0, 'missing': 0}
        
        for i, row in enumerate(songs):
            song = row['song_name']
            movie = row['movie_album']
            
            print(f"[{i+1}/{len(songs)}] {song}...", end=" ", flush=True)
            
            found, content = self.process_song(song, movie)
            
            if found:
                self.save_file(song, movie, content)
                print(f"✓ Found")
                stats['found'] += 1
            else:
                print(f"✗ {content}")
                stats['missing'] += 1
            
            time.sleep(random.uniform(2.0, 4.0))

        self.close()
        print(f"\nCompleted. Found: {stats['found']} | Missing: {stats['missing']}")

if __name__ == "__main__":
    scraper = StealthDeepScraper()
    scraper.run("rawdata/pending_songsv1.csv")