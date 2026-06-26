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
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}

MAX_RETRIES = 3
REQUEST_TIMEOUT = 30
MAX_WORKERS = 3


def _download_single_image(
    session: requests.Session,
    referer: str,
    url: str,
    index: int,
    retries: int = MAX_RETRIES,
) -> tuple[int, Image.Image | None]:
    """Download a single image with retry + backoff. Returns (index, Image) or (index, None)."""
    img_headers = {
        'Referer': referer,
        'Accept': 'image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
        'Sec-Fetch-Dest': 'image',
        'Sec-Fetch-Mode': 'no-cors',
        'Sec-Fetch-Site': 'cross-site',
    }

    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, headers=img_headers, timeout=REQUEST_TIMEOUT)
            r.raise_for_status()

            image_data = io.BytesIO(r.content)
            image = Image.open(image_data)
            if check_image_integrity(image):
                return (index, image)
            else:
                print(f"[WARN] Image at index {index} is corrupted (attempt {attempt}/{retries})")

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else '?'
            print(f"[WARN] HTTP {status} for page {index} (attempt {attempt}/{retries})")
            if status == 403:
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

    print(f"[ERROR] Giving up on image {index}: {url}")
    return (index, None)


def get_images(url: str) -> list[Image.Image]:
    """
    Download all images from an eromanga-show.com viewer page.

    :param url: Viewer page URL, e.g. 'https://eromanga-show.com/viewer?articleId=n&page=n'
    :return: list of PIL Image objects (failed downloads excluded)
    """
    session = requests.Session()
    session.headers.update(_BASE_HEADERS)

    # Step 1: fetch the viewer page
    try:
        r = session.get(url, timeout=REQUEST_TIMEOUT)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Failed to fetch viewer page: {e}")
        return []

    tree = BeautifulSoup(r.content, 'html.parser')
    title = tree.find('title').text
    print(f"Title: {title}")

    # The viewer page URL is the Referer for image requests
    referer = url

    # Step 2: extract image URLs from inline JS
    url_pattern = r'https?://[^\s",]+'
    image_urls = re.findall(url_pattern, tree.findAll('script')[-2].text)

    image_extensions = ('.webp', '.png', '.jpg', '.jpeg')
    images_url_list = []
    for u in image_urls:
        if any(ext in u.lower() for ext in image_extensions):
            images_url_list.append(u.rstrip(',;:"\''))

    if not images_url_list:
        print("[ERROR] No image URLs found on the page.")
        return []

    # Step 3: download images concurrently
    images_dict: dict[int, Image.Image] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {
            executor.submit(_download_single_image, session, referer, img_url, idx): idx
            for idx, img_url in enumerate(images_url_list)
        }
        for future in tqdm(as_completed(futures), total=len(futures), desc="Downloading images"):
            idx, image = future.result()
            if image is not None:
                images_dict[idx] = image

    images = [images_dict[i] for i in sorted(images_dict.keys())]

    missing = len(images_url_list) - len(images)
    if missing > 0:
        print(f"[WARN] {missing}/{len(images_url_list)} pages failed to download and were skipped.")

    print(f'Successfully downloaded: {len(images)}/{len(images_url_list)} images')
    return images
