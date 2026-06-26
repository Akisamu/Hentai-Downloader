from modules import nhentai
from modules.eromanga import get_images
from modules.ptf.i2p import I2P

# ======================================================================
# Mode A — drop nhentai.com URLs here, everything else is automatic
# ======================================================================
nhentai_urls = [
    'https://nhentai.com/en/comic/carpsukidayo-yankee-jk-ntr-kyokon-ochi',
]

# ======================================================================
# Mode B — eromanga-show.com viewer URLs
# ======================================================================
eromanga_urls = [
]

# ======================================================================
# Mode C — manual metadata (if you already know the gallery id / format)
# ======================================================================
infos = [
    # {
    #     'name': "[うるりひ老師 (うるりひ)] 海瀬蒼羽はキミだけのモノになりたい♡ [中国翻訳] [DL版]",
    #     'final': 106,
    #     'id': 581073,
    #     'format': 'webp'
    # },
]


if __name__ == '__main__':
    # ---- Mode A: nhentai.com URLs (auto-scrape) ----
    if nhentai_urls:
        for url in nhentai_urls:
            info = nhentai.scrape_info(url)
            if info is None:
                print(f"[ERROR] Skipping {url} — scraping failed.")
                continue

            print(f"\nProcessing: {info['name']}")
            images = nhentai.get_images(info)
            if images:
                converter = I2P(images=images, pdf_name=info['name'], is_compress=False)
                converter.convert_images_to_pdf()

    # ---- Mode B: eromanga-show.com URLs ----
    if eromanga_urls:
        for item in eromanga_urls:
            print(f"Processing: {item['name']}")
            images = get_images(url=item['url'])
            if images:
                converter = I2P(images=images, pdf_name=item['name'], is_compress=False)
                converter.convert_images_to_pdf()

    # ---- Mode C: manual metadata ----
    if infos:
        for info in infos:
            print(f"Processing: {info['name']}")
            images = nhentai.get_images(info)
            if images:
                converter = I2P(images=images, pdf_name=info['name'], is_compress=False)
                converter.convert_images_to_pdf()
