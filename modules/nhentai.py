import io
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
# Anti-scraping: mimic a real browser as closely as possible
# ---------------------------------------------------------------------------
_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/131.0.0.0 Safari/537.36'
)

_BASE_HEADERS = {
    'User-Agent': _USER_AGENT,
    'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
    'Sec-Fetch-Dest': 'image',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site',
}

MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
MAX_WORKERS = 3

# Try these formats in order when the primary format 404s
FALLBACK_FORMATS = ('webp', 'jpg', 'jpeg', 'png')

# CDN domains to try (auto-detected, these are fallbacks)
CDN_CANDIDATES = [
    'https://cdn.nhentai.com/nhentai/storage/images',
    'https://cdn.cartoonporn.to/nhentai/storage/images',
]


# ======================================================================
#  Scraper — extract {name, final, id, format} from a nhentai.com URL
# ======================================================================

def scrape_info(url: str) -> dict | None:
    """
    Visit a nhentai.com comic page and extract all metadata needed for download.

    :param url: e.g. ``https://nhentai.com/en/comic/<slug>``
    :return:  ``{'name': str, 'final': int, 'id': int, 'format': str, 'cdn_base': str}``
              or *None* if scraping fails.
    """
    print(f"Scraping: {url}")

    # Use minimal headers for the page request — the server is sensitive to
    # Accept / Accept-Encoding and will return stripped-down HTML otherwise.
    page_headers = {
        'User-Agent': _USER_AGENT,
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    }

    # ---- step 1: fetch the main comic page ----
    try:
        r = requests.get(url, headers=page_headers, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch comic page: {e}")
        return None

    soup = BeautifulSoup(r.content, 'html.parser')

    # ---- step 2: extract title ----
    title = _extract_title(soup, url)

    # ---- step 3: extract gallery ID and total pages ----
    gallery_id, final = _extract_id_and_pages(soup, r.text, url)

    if gallery_id is None or final is None:
        print("[ERROR] Could not determine gallery ID or page count.")
        return None

    # ---- step 4: derive CDN base from the thumbnail URL in JSON-LD ----
    cdn_base = _derive_cdn_base_from_page(soup, r.text, gallery_id)

    # ---- step 5: image format — default to webp; the fallback mechanism
    #              in get_images() tries jpg/png automatically on 404 ----
    image_format = 'webp'

    info = {
        'name': title,
        'final': final,
        'id': gallery_id,
        'format': image_format,
        'cdn_base': cdn_base,
    }

    print(f"Scraped: name={info['name']!r}, final={info['final']}, "
          f"id={info['id']}, format={info['format']}, cdn={info['cdn_base']}")
    return info


def _extract_title(soup: BeautifulSoup, url: str) -> str:
    """Extract the doujin title from the page."""
    import json

    # Strategy 1: JSON-LD ComicIssue name (cleanest)
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'ComicIssue':
                name = data.get('name', '').strip()
                if name:
                    return name
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Strategy 2: <title> tag (strip site suffix)
    if soup.title and soup.title.string:
        raw = soup.title.string.strip()
        raw = re.sub(r'\s*[-|]\s*nhentai.*$', '', raw, flags=re.I)
        if len(raw) > 3:
            return raw

    # Strategy 3: og:title / meta
    for meta in soup.find_all('meta'):
        if meta.get('property') in ('og:title', 'twitter:title'):
            content = meta.get('content', '')
            if content:
                return content.strip()

    # Strategy 4: first <h1>
    h1 = soup.find('h1')
    if h1 and h1.text:
        return h1.text.strip()

    # Fallback: derive from URL slug
    slug = url.rstrip('/').rsplit('/', 1)[-1]
    return slug.replace('-', ' ').title()


def _extract_id_and_pages(soup: BeautifulSoup, html: str, url: str) -> tuple[int | None, int | None]:
    """
    Extract (gallery_id, total_pages) using multiple strategies.
    Primary strategy: JSON-LD ComicIssue block.
    """
    gallery_id = None
    final = None

    # ---- Strategy 1: JSON-LD structured data ----
    import json
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if not isinstance(data, dict):
                continue

            # We only care about the ComicIssue block
            if data.get('@type') != 'ComicIssue':
                continue

            # page count
            pages = data.get('numberOfPages')
            if pages:
                final = int(pages)

            # gallery ID — extract from the "image" URL
            # e.g. "https://cdn.nhentai.com/nhentai/storage/comics/616696.jpg"
            image_url = data.get('image', '')
            m = re.search(r'/comics/(\d+)\.', image_url)
            if m:
                gallery_id = int(m.group(1))

        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # ---- Strategy 2: regex on inline JS / data attributes ----
    if not gallery_id:
        for pattern in [
            r'"galleryId"\s*:\s*(\d+)',
            r'data-gallery-id\s*=\s*["\'](\d+)["\']',
            r'/storage/(?:comics|images)/(\d+)',
        ]:
            m = re.search(pattern, html)
            if m:
                gallery_id = int(m.group(1))
                break

    if not final:
        m = re.search(r'(\d+)\s*pages?', html, re.I)
        if m:
            final = int(m.group(1))

    # ---- Strategy 3: count reader-page links ----
    if not final:
        reader_links = soup.find_all('a', href=re.compile(r'/reader/\d+'))
        page_nums = set()
        for a in reader_links:
            m = re.search(r'/reader/(\d+)', a.get('href', ''))
            if m:
                page_nums.add(int(m.group(1)))
        if page_nums:
            final = max(page_nums)

    return gallery_id, final


def _derive_cdn_base_from_page(soup: BeautifulSoup, html: str, gallery_id: int) -> str:
    """
    Derive the CDN base URL from the main page.
    Looks at the JSON-LD ``image`` field and the ``<link rel="preconnect">`` tag.
    Falls back to CDN_CANDIDATES[0].
    """
    import json

    # Strategy 1: extract from JSON-LD image URL
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict) and data.get('@type') == 'ComicIssue':
                image_url = data.get('image', '')
                if image_url:
                    cdn = _derive_cdn_base(image_url, gallery_id)
                    # The 'image' field points to .../comics/<id>.jpg
                    # We need .../images for page downloads
                    return cdn.replace('/comics', '/images')
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

    # Strategy 2: <link rel="preconnect"> tag
    for link in soup.find_all('link', rel='preconnect'):
        href = link.get('href', '')
        if 'cdn' in href or 'cdn3' in href:
            # e.g. https://cdn.nhentai.com or https://cdn3.hentok.com
            return href.rstrip('/') + '/nhentai/storage/images'

    # Fallback
    return CDN_CANDIDATES[0]


def _derive_cdn_base(image_url: str, gallery_id: int) -> str:
    """Given a full CDN image URL, return the base path (schema + path up to the gallery id)."""
    # e.g. https://cdn.nhentai.com/nhentai/storage/images/616696/2.webp
    #   -> https://cdn.nhentai.com/nhentai/storage/images
    idx = image_url.find(f'/storage/images/{gallery_id}')
    if idx != -1:
        return image_url[:idx + len(f'/storage/images')]
    # Fallback
    return CDN_CANDIDATES[0]


# ======================================================================
#  Image downloader
# ======================================================================

def _build_session(gallery_url: str) -> tuple[requests.Session, str]:
    """
    Create a requests.Session, visit the gallery page to seed cookies,
    and return (session, referer) for use in image downloads.
    """
    session = requests.Session()
    session.headers.update(_BASE_HEADERS)
    session.headers['Referer'] = 'https://nhentai.net/'

    try:
        r = session.get(gallery_url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
        print(f"Visited gallery page: {r.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"[WARN] Could not reach gallery page: {e}")

    return session, gallery_url


def _download_single_image(
    session: requests.Session,
    referer: str,
    urls: list[str],
    index: int,
    retries: int = MAX_RETRIES,
) -> tuple[int, Image.Image | None]:
    """Download a single image, trying each URL in *urls* as fallback.
    Returns (index, Image) or (index, None) if all URLs are exhausted."""
    img_headers = {'Referer': referer}

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


def get_images(info: dict) -> list[Image.Image]:
    """
    Download all images for a doujin from nhentai CDN.

    :param info: dict with keys 'final', 'id', 'format', and optionally 'cdn_base' and 'name'
    :return: list of PIL Image objects (failed downloads excluded)
    """
    final = info['final']
    doujin_id = info['id']
    image_format = info['format']
    cdn_base = info.get('cdn_base', CDN_CANDIDATES[0])

    # Build gallery URL for the referer / session
    gallery_url = f'https://nhentai.net/g/{doujin_id}/'

    # Order: user-specified format first, then remaining fallback formats
    ordered_formats = [image_format] + [f for f in FALLBACK_FORMATS if f != image_format]

    tasks: list[tuple[list[str], int]] = []
    for i in range(1, final + 1):
        urls = [f'{cdn_base}/{doujin_id}/{i}.{fmt}' for fmt in ordered_formats]
        tasks.append((urls, i))

    session, referer = _build_session(gallery_url)

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
