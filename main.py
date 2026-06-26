import os

from modules import nhentai
from modules.utils import record_history, save_thumbnail
from modules.eromanga import get_images, scrape_info as scrape_eromanga
from modules.ptf.i2p import I2P


def _download_and_convert(info: dict, images: list, name: str, url: str):
    """Shared pipeline: download images → thumbnail → PDF → history."""
    if not images:
        print(f"[WARN] No images for {name!r} — skipping PDF generation.")
        return

    thumb_path = save_thumbnail(images[0], I2P.output_dir, name)

    converter = I2P(images=images, pdf_name=name, is_compress=False)
    converter.convert_images_to_pdf()

    total = info.get('final', len(images))
    record_history(
        I2P.output_dir,
        name=name,
        url=url,
        total=total,
        downloaded=len(images),
        thumb=os.path.basename(thumb_path),
    )


# ======================================================================
# Mode A — drop nhentai.com URLs here, everything else is automatic
# ======================================================================
nhentai_urls = [
    'https://nhentai.com/en/comic/carpsukidayo-yankee-jk-ntr-kyokon-ochi',
]

# ======================================================================
# Mode B — drop eromanga-show.com article URLs here
# ======================================================================
eromanga_urls = [
    'https://eromanga-show.com/articles/2920939',
]

# ======================================================================
# Mode C — manual metadata (if you already know the gallery id / format)
#   Format: {'name': str, 'final': int, 'id': int, 'format': str}
# ======================================================================
infos = [
]


if __name__ == '__main__':
    # ---- Mode A: nhentai.com URLs (auto-scrape) ----
    for url in nhentai_urls:
        info = nhentai.scrape_info(url)
        if info is None:
            print(f"[ERROR] Skipping {url} — scraping failed.")
            continue
        print(f"\nProcessing: {info['name']}")
        _download_and_convert(info, nhentai.get_images(info), info['name'], url)

    # ---- Mode B: eromanga-show.com article URLs (auto-scrape) ----
    for url in eromanga_urls:
        info = scrape_eromanga(url)
        if info is None:
            print(f"[ERROR] Skipping {url} — scraping failed.")
            continue
        print(f"\nProcessing: {info['name']}")
        _download_and_convert(info, get_images(url), info['name'], url)

    # ---- Mode C: manual metadata ----
    for info in infos:
        url = f"https://nhentai.net/g/{info['id']}/"
        print(f"Processing: {info['name']}")
        _download_and_convert(info, nhentai.get_images(info), info['name'], url)
