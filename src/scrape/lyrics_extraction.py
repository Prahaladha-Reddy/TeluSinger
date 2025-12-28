import requests
import json
from bs4 import BeautifulSoup
import csv
import time
import re
import logging
from pathlib import Path
from dataclasses import dataclass
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()
import os
SERPER_API_KEY=os.getenv("SERPER_API_KEY")
OUTPUT_DIR = "lyrics_serper_tape"
REQUEST_DELAY = 1.0
MIN_TELUGU_CHARS = 30 

logging.basicConfig(level=logging.INFO, format='%(message)s')
log = logging.getLogger(__name__)

@dataclass
class LyricsResult:
    found: bool
    lyrics: str = ""
    source: str = ""
    url: str = ""

class LyricstapeSerperScraper:
    def __init__(self, api_key):
        self.api_key = api_key
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def is_telugu(self, text):
        return bool(re.search(r'[\u0C00-\u0C7F]', text))

    def count_telugu_chars(self, text):
        return len(re.findall(r'[\u0C00-\u0C7F]', text))

    def clean_text(self, text):
        if not text: return ""
        lines = [line.strip() for line in text.split('\n')]
        cleaned = []
        for line in lines:
            if not line: continue
            
            low = line.lower()
            if any(x in low for x in ['home', 'movie', 'review', 'rating', 'whatsapp', 'share', 'tweet', 'pin it']):
                continue
            
            if self.is_telugu(line):
                cleaned.append(line)
                
        return '\n'.join(cleaned)

    def get_lyricstape_urls(self, song, movie):
        url = "https://google.serper.dev/search"
        
        query = f"site:lyricstape.com {song} {movie} lyrics"
        
        payload = json.dumps({
            "q": query,
            "gl": "in",
            "hl": "en",
            "num": 3  
        })
        
        headers = {
            'X-API-KEY': self.api_key,
            'Content-Type': 'application/json'
        }

        try:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code != 200:
                return []
                
            data = response.json()
            valid_urls = []
            
            if "organic" in data:
                for item in data["organic"]:
                    link = item.get("link")
                    if link and "lyricstape.com" in link:
                        valid_urls.append(link)
            
            return valid_urls
            
        except Exception as e:
            log.error(f"Search Request Error: {e}")
            return []

    def extract_lyrics(self, soup):

        for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'iframe']):
            tag.decompose()

        best_text = ""
        max_score = 0
        
        for elem in soup.find_all(['div', 'article', 'p']):
            text = elem.get_text(separator='\n')
            score = self.count_telugu_chars(text)
            
            if score > max_score:
                max_score = score
                best_text = text

        if max_score >= MIN_TELUGU_CHARS:
            return self.clean_text(best_text)
            
        return None

    def process_song(self, song, movie):
        urls = self.get_lyricstape_urls(song, movie)
        
        for url in urls:
            try:
                resp = requests.get(url, headers=self.headers, timeout=10)
                if resp.status_code != 200: continue
                
                soup = BeautifulSoup(resp.content, 'html.parser')
                lyrics = self.extract_lyrics(soup)
                
                if lyrics:
                    return LyricsResult(True, lyrics, "lyricstape.com", url)
                    
            except Exception:
                continue
                
        return LyricsResult(False)

    def save_file(self, song, movie, result):
        clean_movie = re.sub(r'[^\w\-_]', '', movie.replace(' ', '_'))
        clean_song = re.sub(r'[^\w\-_]', '', song.replace(' ', '_'))
        
        folder = self.output_dir / clean_movie
        folder.mkdir(exist_ok=True)
        
        path = folder / f"{clean_song}.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"Song: {song}\nMovie: {movie}\nSource: {result.source}\nURL: {result.url}\n\n{result.lyrics}")

    def run(self, csv_file):
        with open(csv_file, 'r', encoding='utf-8') as f:
            songs = list(csv.DictReader(f))
            
        total = len(songs)
        print(f"--- Starting Serper (Lyricstape Only) on {total} songs ---")
        
        stats = {'found': 0, 'missing': 0}
        
        for i, row in enumerate(songs):
            song = row['song_name']
            movie = row['movie_album']
            
            print(f"[{i+1}/{total}] {song}...", end=" ", flush=True)
            
            result = self.process_song(song, movie)
            
            if result.found:
                self.save_file(song, movie, result)
                print(f"✓ Found")
                stats['found'] += 1
            else:
                print("✗ Not found on Lyricstape")
                stats['missing'] += 1
                
            time.sleep(REQUEST_DELAY)

if __name__ == "__main__":
    MY_SERPER_KEY = SERPER_API_KEY
    
    scraper = LyricstapeSerperScraper(api_key=MY_SERPER_KEY)
    scraper.run("sirivennela_songs.csv")