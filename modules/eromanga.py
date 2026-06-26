"""Download images from eromanga-show.com articles."""
import io
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image
from bs4 import BeautifulSoup
from tqdm import tqdm

from modules.Utils import check_image_integrity

# ---------------------------------------------------------------------------
# Anti-scraping
# ---------------------------------------------------------------------------
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)

_PAGE_HEADERS = {
    'User-Agent': _USER_AGENT,
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
}

_IMG_HEADERS = {
    'User-Agent': _USER_AGENT,
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
}

MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
MAX_WORKERS = 3

FALLBACK_FORMATS = ('webp', 'jpg', 'jpeg', 'png')

# ======================================================================
#  Scraper — extract metadata from an eromanga-show.com article page
# ======================================================================

def scrape_info(url: str) -> dict | None:
    """
    Visit an eromanga-show.com article page and extract metadata.

    :param url: e.g. ``https://eromanga-show.com/articles/2920939``
    :return:  ``{'name': str, 'final': int, 'article_id': int}`` or *None*
    """
    print(f"Scraping: {url}")

    # ---- step 1: fetch the article page ----
    try:
        r = requests.get(url, headers=_PAGE_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch article page: {e}")
        return None

    soup = BeautifulSoup(r.content, 'html.parser')

    # ---- step 2: extract article ID from URL ----
    m = re.search(r'/articles/(\d+)', url)
    article_id = int(m.group(1)) if m else None
    if article_id is None:
        print("[ERROR] Could not determine article ID from URL.")
        return None

    # ---- step 3: extract title ----
    title = _extract_title(soup, url, article_id)

    # ---- step 4: count pages from viewer links ----
    final = _count_pages(soup, article_id)
    if final is None:
        print("[ERROR] Could not determine page count.")
        return None

    info = {'name': title, 'final': final, 'article_id': article_id}
    print(f"Scraped: name={info['name']!r}, final={info['final']}, article_id={info['article_id']}")
    return info


def _extract_title(soup: BeautifulSoup, url: str, article_id: int) -> str:
    """Extract the doujin title from the article page. Falls back to ``eromanga-<id>``."""
    # Strategy 1: og:title
    for meta in soup.find_all('meta'):
        if meta.get('property') == 'og:title':
            content = meta.get('content', '').strip()
            if content:
                return content

    # Strategy 2: <title> — strip site suffix
    if soup.title and soup.title.string:
        raw = soup.title.string.strip()
        # Remove " - SiteName" suffixes (English and Japanese kanji/kana variants)
        raw = re.sub(r'\s*[-‒–—|]\s*(?:Eromanga|エロ漫画|エロマンガ|eromanga)\s*(?:Show|SHOW|show).*$', '', raw, flags=re.I)
        if len(raw) > 3:
            return raw

    # Strategy 3: <h1>
    h1 = soup.find('h1')
    if h1 and h1.text:
        return h1.text.strip()

    # Fallback
    return f'eromanga-{article_id}'


def _count_pages(soup: BeautifulSoup, article_id: int) -> int | None:
    """Count total pages by finding the highest page number in viewer links."""
    max_page = 0
    for a in soup.find_all('a', href=re.compile(r'/viewer\?articleId=' + str(article_id) + r'&page=\d+')):
        m = re.search(r'page=(\d+)', a.get('href', ''))
        if m:
            max_page = max(max_page, int(m.group(1)))
    return max_page if max_page > 0 else None


def _extract_slides(article_id: int) -> list[str] | None:
    """
    Visit the viewer page and extract the full ``slides`` array
    (all CDN image URLs) from the Next.js RSC data.
    """
    viewer_url = f'https://eromanga-show.com/viewer?articleId={article_id}&page=1'

    try:
        r = requests.get(viewer_url, headers=_PAGE_HEADERS, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch viewer page: {e}")
        return None

    # The image list lives in an inline script as:
    #   "slides":[{"src":"https://cdn.../1.webp"},{"src":"https://cdn.../2.webp"},...]
    # Strategy 1: try parsing as JSON fragment
    m = re.search(r'"slides"\s*:\s*(\[.+?\])', r.text, re.DOTALL)
    if m:
        try:
            slides = json.loads(m.group(1))
            urls = [s['src'] for s in slides if 'src' in s]
            if urls:
                return urls
        except (json.JSONDecodeError, KeyError):
            pass

    # Strategy 2: regex extract all CDN image URLs from the raw text
    cdn_pattern = re.compile(
        r'https?://cdn\.imagedeliveries\.com/' + str(article_id) + r'/[^"\s<>]+\.(?:webp|jpg|jpeg|png)'
    )
    urls = list(dict.fromkeys(cdn_pattern.findall(r.text)))  # dedup, preserve order
    if urls:
        return urls

    print("[ERROR] No image URLs found on viewer page.")
    return None


# ======================================================================
#  Image downloader
# ======================================================================

def _download_single_image(
    session: requests.Session,
    referer: str,
    urls: list[str],
    index: int,
    retries: int = MAX_RETRIES,
) -> tuple[int, Image.Image | None]:
    """Download a single image, trying each URL in *urls* as fallback.
    Returns (index, Image) or (index, None) if all URLs exhausted."""
    img_headers = {'Referer': referer, **_IMG_HEADERS}

    for url_idx, url in enumerate(urls):
        fmt = url.rsplit('.', 1)[-1] if '.' in url else '?'
        for attempt in range(1, retries + 1):
            try:
                r = session.get(url, headers=img_headers, timeout=REQUEST_TIMEOUT)
                r.raise_for_status()

                image_data = io.BytesIO(r.content)
                image = Image.open(image_data)
                if check_image_integrity(image):
                    if url_idx > 0:
                        print(f"[INFO] Page {index}: fell back to .{fmt} successfully")
                    return (index, image)
                else:
                    print(f"[WARN] Image at index {index} is corrupted (attempt {attempt}/{retries})")

            except requests.exceptions.HTTPError as e:
                status = e.response.status_code if e.response is not None else '?'
                if url_idx == 0:
                    print(f"[WARN] HTTP {status} for page {index} (attempt {attempt}/{retries})")
                if status == 404:
                    break
                elif status == 403:
                    time.sleep(random.uniform(2, 5))
                elif status == 429:
                    time.sleep(random.uniform(5, 10))
            except requests.exceptions.RequestException as e:
                print(f"[WARN] Network error for page {index} (attempt {attempt}/{retries}): {e}")
            except Exception as e:
                print(f"[WARN] Unexpected error for page {index} (attempt {attempt}/{retries}): {e}")

            if attempt < retries:
                delay = random.uniform(1, 3) * (2 ** (attempt - 1))
                time.sleep(delay)

    print(f"[ERROR] Giving up on page {index}: all formats exhausted")
    return (index, None)


def get_images(url: str) -> list[Image.Image]:
    """
    Download all images from an eromanga-show.com article.

    :param url: article page URL, e.g. ``https://eromanga-show.com/articles/2920939``
    :return: list of PIL Image objects (failed downloads excluded)
    """
    # ---- scrape metadata ----
    info = scrape_info(url)
    if info is None:
        return []

    article_id = info['article_id']
    final = info['final']

    # ---- extract image URLs from the viewer page ----
    slides = _extract_slides(article_id)
    if not slides:
        return []

    # Truncate or pad to match expected page count
    if len(slides) > final:
        slides = slides[:final]
    elif len(slides) < final:
        print(f"[WARN] Slides array has {len(slides)} entries but expected {final} pages.")

    final = len(slides)

    # Build fallback URLs for each page (the hash makes this tricky, so we
    # only use format fallbacks for the primary URL)
    image_format = slides[0].rsplit('.', 1)[-1] if slides else 'webp'
    alt_formats = [f for f in FALLBACK_FORMATS if f != image_format]

    tasks: list[tuple[list[str], int]] = []
    for i, primary_url in enumerate(slides, start=1):
        urls = [primary_url]
        base = primary_url.rsplit('.', 1)[0]
        urls += [f'{base}.{fmt}' for fmt in alt_formats]
        tasks.append((urls, i))

    # ---- download ----
    session = requests.Session()
    session.headers.update(_PAGE_HEADERS)
    referer = f'https://eromanga-show.com/articles/{article_id}'

    images_dict: dict[int, Image.Image] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_download_single_image, session, referer, urls, idx): idx
            for urls, idx in tasks
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading images"):
            idx, image = future.result()
            if image is not None:
                images_dict[idx] = image

    images = [images_dict[i] for i in sorted(images_dict.keys())]

    missing = final - len(images)
    if missing > 0:
        print(f"[WARN] {missing}/{final} pages failed to download and were skipped.")

    print(f'Successfully downloaded: {len(images)}/{final} images')
    return images
