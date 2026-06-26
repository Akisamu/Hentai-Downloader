"""Legacy test script — download images to disk, then convert to PDF via ptf."""
import os
import subprocess

import requests
from tqdm import tqdm

name = '[Funabori Nariaki] Chokyo Soudanshitsu | 调教相谈室 [Chinese] [Digital]'
final = 212
gallery_id = 554479
image_format = 'jpg'
output_dir = os.path.join(os.path.expanduser('~'), 'Desktop', 'output')

os.makedirs(output_dir, exist_ok=True)

for i in tqdm(range(1, final + 1), desc="Downloading"):
    url = f'https://cdn.cartoonporn.to/nhentai/storage/images/{gallery_id}/{i}.{image_format}'

    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to download page {i}: {e}")
        continue

    filepath = os.path.join(output_dir, f'{i}.jpg')
    with open(filepath, 'wb') as out_file:
        out_file.write(r.content)

# Convert to PDF (requires `ptf` on PATH or run from the ptf directory)
subprocess.run(['python', 'ptf.py'], cwd=os.path.dirname(os.path.abspath(__file__)))
print(f"Done. Output in: {output_dir}")
