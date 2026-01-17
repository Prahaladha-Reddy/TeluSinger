import time
import re
import json
import logging
import random
import shutil
from pathlib import Path
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import undetected_chromedriver as uc
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock
import threading

# Configuration
OUTPUT_DIR = "sirivennela_lyrics"
PROGRESS_FILE = "scraping_progress.json"
BASE_URL = "https://www.lyricstape.com"
LYRICIST_URL = "https://www.lyricstape.com/lyricist-details/1"
MIN_TELUGU_CHARS = 30
NUM_WORKERS = 4  # 4 parallel headless browsers

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(threadName)s] %(message)s',
    datefmt='%H:%M:%S'
)
log = logging.getLogger(__name__)

# Thread-safe locks
progress_lock = Lock()
stats_lock = Lock()
driver_init_lock = Lock()  # Prevents concurrent driver patching


class BrowserWorker:
    def __init__(self, worker_id):
        self.worker_id = worker_id
        self.driver = None
    
    def start(self):
        # Sequential driver init to prevent file conflicts
        with driver_init_lock:
            log.info(f"Worker {self.worker_id}: Initializing browser...")
            self.driver = self._setup_driver()
            time.sleep(1)  # Small delay between inits
        return self
    
    def _setup_driver(self):
        options = uc.ChromeOptions()
        # Minimized window instead of headless (headless crashes on Windows)
        options.add_argument('--start-minimized')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-extensions')
        options.add_argument('--blink-settings=imagesEnabled=false')
        options.add_argument('--window-size=800,600')
        options.add_argument('--disable-background-networking')
        options.add_argument('--disable-default-apps')
        options.add_argument('--disable-sync')
        options.add_argument('--mute-audio')
        
        # Unique user data dir per worker (Windows compatible)
        user_data = Path.home() / f".chrome_worker_{self.worker_id}"
        if user_data.exists():
            shutil.rmtree(user_data, ignore_errors=True)
        user_data.mkdir(exist_ok=True)
        options.add_argument(f'--user-data-dir={user_data}')
        
        driver = uc.Chrome(options=options, version_main=143)
        driver.set_window_position(-2000, 0)  # Move off-screen
        return driver
    
    def get_page(self, url, wait_time=2.0):
        for attempt in range(3):
            try:
                self.driver.get(url)
                time.sleep(wait_time + random.uniform(0.5, 1.5))
                return self.driver.page_source
            except Exception as e:
                log.warning(f"Worker {self.worker_id} attempt {attempt+1} failed: {e}")
                time.sleep(2)
        return None
    
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass


class ParallelSirivenellaScraper:
    def __init__(self):
        self.output_dir = Path(OUTPUT_DIR)
        self.output_dir.mkdir(exist_ok=True)
        self.progress = self._load_progress()
        self.stats = {"scraped": 0, "failed": 0, "skipped": 0}
        self.main_driver = None
    
    def _load_progress(self):
        if Path(PROGRESS_FILE).exists():
            with open(PROGRESS_FILE) as f:
                data = json.load(f)
                data['scraped_songs'] = set(data.get('scraped_songs', []))
                return data
        return {"scraped_songs": set()}
    
    def _save_progress(self):
        with progress_lock:
            data = {"scraped_songs": list(self.progress['scraped_songs'])}
            with open(PROGRESS_FILE, 'w') as f:
                json.dump(data, f)
    
    def _setup_main_driver(self):
        """Single driver for initial page fetch - patches driver once"""
        log.info("Fetching lyricist page to get all movies...")
        options = uc.ChromeOptions()
        options.add_argument('--start-minimized')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--blink-settings=imagesEnabled=false')
        self.main_driver = uc.Chrome(options=options, version_main=143)
        self.main_driver.set_window_position(-2000, 0)  # Off-screen
        time.sleep(2)
        return self.main_driver
    
    def extract_movies_by_year(self):
        driver = self._setup_main_driver()
        driver.get(LYRICIST_URL)
        time.sleep(4)
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        movies_by_year = {}
        
        # Find all h4 year headers (#### 2023 etc)
        year_headers = soup.find_all('h4')
        
        for header in year_headers:
            year_text = header.get_text(strip=True)
            year_match = re.search(r'\d{4}', year_text)
            if not year_match:
                continue
            
            year = year_match.group()
            movies_by_year[year] = []
            
            # Get all sibling elements until next h4
            sibling = header.find_next_sibling()
            while sibling and sibling.name != 'h4':
                # Find all album links in this section
                if sibling.name == 'a' and sibling.get('href'):
                    href = sibling['href']
                    if '/album/' in href:
                        movies_by_year[year].append({
                            'name': sibling.get_text(strip=True),
                            'url': urljoin(BASE_URL, href),
                            'year': year
                        })
                # Also check for links inside the sibling
                for link in sibling.find_all('a', href=True) if hasattr(sibling, 'find_all') else []:
                    href = link['href']
                    if '/album/' in href:
                        movies_by_year[year].append({
                            'name': link.get_text(strip=True),
                            'url': urljoin(BASE_URL, href),
                            'year': year
                        })
                sibling = sibling.find_next_sibling()
        
        # Fallback: just get ALL album links on page
        if not movies_by_year or sum(len(v) for v in movies_by_year.values()) == 0:
            log.info("Using fallback: extracting all album links...")
            movies_by_year = {'unknown': []}
            for link in soup.find_all('a', href=True):
                href = link['href']
                if '/album/' in href and 'Lid-1' in href:
                    movies_by_year['unknown'].append({
                        'name': link.get_text(strip=True),
                        'url': urljoin(BASE_URL, href),
                        'year': 'unknown'
                    })
        
        driver.quit()
        self.main_driver = None
        return movies_by_year
    
    def extract_songs_from_movie(self, worker, movie_url):
        html = worker.get_page(movie_url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        songs = []
        seen_urls = set()
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            # Song URLs contain "-song-lyrics" pattern
            if '-song-lyrics' in href:
                full_url = urljoin(BASE_URL, href)
                if full_url not in seen_urls:
                    seen_urls.add(full_url)
                    # Get song name - clean up the text
                    name = link.get_text(strip=True)
                    # Remove "..." truncation artifacts
                    name = re.sub(r'\.{2,}', '', name).strip()
                    
                    if name:
                        songs.append({
                            'name': name,
                            'url': full_url
                        })
        
        return songs
    
    def extract_lyrics(self, worker, song_url):
        html = worker.get_page(song_url)
        if not html:
            return None, {}
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Lyrics are in 6 tags - first one is Telugu, second is English transliteration
        h6_tags = soup.find_all('h6')
        
        telugu_lyrics = None
        english_lyrics = None
        
        for h6 in h6_tags:
            text = h6.get_text('\n', strip=True)
            telugu_count = len(re.findall(r'[\u0C00-\u0C7F]', text))
            
            if telugu_count >= MIN_TELUGU_CHARS:
                telugu_lyrics = text
            elif len(text) > 50 and not telugu_lyrics:
                english_lyrics = text
        
        # Prefer Telugu lyrics
        lyrics = telugu_lyrics or english_lyrics
        
        if not lyrics:
            # Fallback search for other containers if h6 fails
            lyrics_div = soup.find('div', class_=re.compile(r'lyrics|content', re.I))
            if not lyrics_div:
                lyrics_div = soup.find('pre')
            if not lyrics_div:
                lyrics_div = soup.find('article')
                
            if lyrics_div:
                lyrics = lyrics_div.get_text('\n', strip=True)
            else:
                return None, {}
        
        # Check minimum Telugu content again if we used fallback
        telugu_count = len(re.findall(r'[\u0C00-\u0C7F]', lyrics))
        if telugu_count < MIN_TELUGU_CHARS and not english_lyrics:
            return None, {}
        
        # Extract metadata
        metadata = {'url': song_url}
        
        # Helper to safely extract metadata
        def get_meta(pattern):
            el = soup.find(string=re.compile(pattern, re.I))
            if el and el.parent:
                return el.parent.get_text(strip=True).replace(pattern.replace('^', '').replace(':', ''), '').strip()
            return "Unknown"

        metadata['song'] = get_meta(r'^Song:')
        metadata['lyricist'] = get_meta(r'^Lyricist:')
        metadata['singers'] = get_meta(r'^Singers:')
        metadata['movie'] = get_meta(r'^Movie:')
        metadata['year'] = get_meta(r'^Year:')
        metadata['music_director'] = get_meta(r'^Music Director:')
        
        return lyrics, metadata
    
    def save_lyrics(self, year, movie_name, song_name, lyrics, metadata, url):
        # Sanitize names
        safe_movie = re.sub(r'[<>:"/\\|?*]', '_', movie_name)[:50]
        safe_song = re.sub(r'[<>:"/\\|?*]', '_', song_name)[:50]
        
        movie_dir = self.output_dir / year / safe_movie
        movie_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = movie_dir / f"{safe_song}.txt"
        
        content = f"Song: {song_name}\nMovie: {movie_name}\nYear: {year}\nURL: {url}\n"
        for k, v in metadata.items():
            if k != 'url':
                content += f"{k.title()}: {v}\n"
        content += f"\n{'='*50}\n\n{lyrics}"
        
        filepath.write_text(content, encoding='utf-8')
    
    def process_movie(self, worker, movie):
        movie_url = movie['url']
        movie_name = movie['name']
        year = movie['year']
        
        songs = self.extract_songs_from_movie(worker, movie_url)
        results = {'scraped': 0, 'failed': 0, 'skipped': 0}
        
        for song in songs:
            song_url = song['url']
            song_name = song['name']
            
            if song_url in self.progress['scraped_songs']:
                results['skipped'] += 1
                continue
            
            lyrics, metadata = self.extract_lyrics(worker, song_url)
            
            if lyrics:
                self.save_lyrics(year, movie_name, song_name, lyrics, metadata, song_url)
                results['scraped'] += 1
                
                with progress_lock:
                    self.progress['scraped_songs'].add(song_url)
                
                log.info(f"✓ {year}/{movie_name}/{song_name}")
            else:
                results['failed'] += 1
            
            time.sleep(random.uniform(0.8, 1.5))
        
        return results
    
    def worker_task(self, worker_id, movies_chunk):
        worker = BrowserWorker(worker_id)
        
        try:
            worker.start()  # Sequential init with lock
            log.info(f"Worker {worker_id} started with {len(movies_chunk)} movies")
            
            local_stats = {"scraped": 0, "failed": 0, "skipped": 0}
            
            for i, movie in enumerate(movies_chunk):
                log.info(f"Worker {worker_id}: [{i+1}/{len(movies_chunk)}] {movie['year']} - {movie['name']}")
                
                result = self.process_movie(worker, movie)
                local_stats['scraped'] += result['scraped']
                local_stats['failed'] += result['failed']
                local_stats['skipped'] += result['skipped']
                
                if (i + 1) % 5 == 0:
                    self._save_progress()
                
                time.sleep(random.uniform(1.0, 2.0))
            
            return local_stats
        
        except Exception as e:
            log.error(f"Worker {worker_id} error: {e}")
            return {"scraped": 0, "failed": 0, "skipped": 0}
        
        finally:
            worker.close()
    
    def run(self):
        log.info("="*60)
        log.info(f"  Sirivennela Lyrics Scraper - {NUM_WORKERS} Parallel Browsers")
        log.info("="*60)
        
        movies_by_year = self.extract_movies_by_year()
        
        all_movies = []
        for year in sorted(movies_by_year.keys(), reverse=True):
            for movie in movies_by_year[year]:
                all_movies.append(movie)
        
        total_movies = len(all_movies)
        log.info(f"\nFound {total_movies} movies to process")
        log.info(f"Already scraped: {len(self.progress['scraped_songs'])} songs")
        
        if total_movies == 0:
            log.error("No movies found! Check if the page loaded correctly.")
            return
        
        chunk_size = max(1, (total_movies + NUM_WORKERS - 1) // NUM_WORKERS)
        chunks = [all_movies[i:i + chunk_size] for i in range(0, total_movies, chunk_size)]
        
        log.info(f"\nSplitting work across {NUM_WORKERS} workers:")
        for i, chunk in enumerate(chunks):
            if chunk:
                years = set(m['year'] for m in chunk)
                log.info(f"  Worker {i}: {len(chunk)} movies ({min(years)}-{max(years)})")
        
        log.info("\nStarting parallel scraping...")
        
        with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
            futures = []
            for i, chunk in enumerate(chunks):
                if chunk:
                    future = executor.submit(self.worker_task, i, chunk)
                    futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    with stats_lock:
                        self.stats['scraped'] += result['scraped']
                        self.stats['failed'] += result['failed']
                        self.stats['skipped'] += result['skipped']
                except Exception as e:
                    log.error(f"Worker failed: {e}")
        
        self._save_progress()
        self._print_stats()
    
    def _print_stats(self):
        log.info(f"\n{'='*60}")
        log.info("  SCRAPING COMPLETE")
        log.info(f"{'='*60}")
        log.info(f"  New songs scraped:  {self.stats['scraped']}")
        log.info(f"  Skipped (existing): {self.stats['skipped']}")
        log.info(f"  Failed:              {self.stats['failed']}")
        log.info(f"  Total in database:  {len(self.progress['scraped_songs'])}")
        log.info(f"\n  Output: {self.output_dir.absolute()}")
        log.info(f"{'='*60}\n")


if __name__ == "__main__":
    scraper = ParallelSirivenellaScraper()
    try:
        scraper.run()
    except KeyboardInterrupt:
        log.info("\nInterrupted! Saving progress...")
        scraper._save_progress()
    except Exception as e:
        log.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        scraper._save_progress()