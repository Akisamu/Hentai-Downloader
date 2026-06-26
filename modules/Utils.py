import io
import json
import os
import shutil
import subprocess
import uuid
from datetime import datetime, timezone

import PIL
from PIL import Image


def check_image_integrity(image: Image.Image) -> bool:
    """Verify that a PIL Image can be fully loaded without corruption."""
    try:
        image.load()
        return True
    except (IOError, PIL.UnidentifiedImageError) as e:
        print(f"Image is corrupted or invalid. Error: {e}")
        return False


def compress_image(
    image: Image.Image,
    jpeg_quality: int = 85,
    max_dimension: int | None = None,
) -> Image.Image:
    """
    Compress a single PIL Image for PDF embedding.

    Techniques applied (all lossless or near-lossless):
      1. RGBA / P / LA → flat RGB (white background) — removes useless alpha channels
      2. Optional downscale if *max_dimension* is set and the image exceeds it
      3. Re-encode as optimised JPEG at *jpeg_quality* (85 = great balance)

    Returns a new RGB Image; the original is never mutated.

    Size reduction examples (1280×1810 scan):
      - Original PNG/webp in PDF  →  ~2 – 6 MB / page
      - After compress_image(85)  →  ~200 – 500 KB / page  (≈10× smaller)
    """
    img = image.copy()

    # ---- step 1: flatten transparency onto white background ----
    if img.mode == 'P':
        img = img.convert('RGBA')

    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[3])  # alpha channel as mask
        else:  # LA
            background.paste(img, mask=img.split()[1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')

    # ---- step 2: optional downscale (preserves aspect ratio) ----
    if max_dimension and max(img.size) > max_dimension:
        ratio = max_dimension / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # ---- step 3: re-encode as optimised JPEG ----
    buf = io.BytesIO()
    img.save(buf, format='JPEG', quality=jpeg_quality, optimize=True, progressive=False)
    buf.seek(0)

    return Image.open(buf)


def compress_images(
    images: list[Image.Image],
    jpeg_quality: int = 85,
    max_dimension: int | None = None,
) -> list[Image.Image]:
    """Batch version of :func:`compress_image` — returns a new list."""
    return [compress_image(img, jpeg_quality, max_dimension) for img in images]


def get_file_size_mb(path: str) -> float:
    """Return file size in megabytes (MiB), or 0 if the file doesn't exist."""
    if not os.path.exists(path):
        return 0.0
    return os.path.getsize(path) / (1024 * 1024)


def compress_existing_pdf(input_path: str, output_path: str | None = None) -> str | None:
    """
    Compress an already-generated PDF.

    Tries Ghostscript first (best quality / smallest output).
    Falls back to a pure-Python message if Ghostscript is not installed.

    :param input_path:  path to the original PDF
    :param output_path: destination path; defaults to ``<dir>/[C]<basename>``
    :return: path to the compressed file, or *None* on failure
    """
    if output_path is None:
        directory = os.path.dirname(input_path) or '.'
        basename = os.path.basename(input_path)
        output_path = os.path.join(directory, f'[C]{basename}')

    # ---- method 1: Ghostscript (produces the best results) ----
    if shutil.which('gs'):
        subprocess.call([
            'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_path}', input_path,
        ])
        if os.path.exists(output_path):
            before = get_file_size_mb(input_path)
            after = get_file_size_mb(output_path)
            print(f"PDF compressed: {before:.1f} MB → {after:.1f} MB  ({output_path})")
            return output_path
        else:
            print("[WARN] Ghostscript ran but produced no output. Keeping original.")
            return None

    # ---- method 2: pure-Python fallback ----
    print("[INFO] Ghostscript not found. For post-PDF compression install it:")
    print("         scoop install ghostscript   (Windows)")
    print("         brew install ghostscript    (macOS)")
    print("         apt install ghostscript     (Linux)")
    print("       Or set is_compress=True / I2P(image_quality=85) for built-in JPEG compression.")
    return None


# ======================================================================
#  Download history  (stored under ``<output_dir>/history/``)
# ======================================================================

def _history_dir(output_dir: str) -> str:
    """Return the path to the .history folder (create it if missing)."""
    path = os.path.join(output_dir, 'history')
    # If an old flat file exists, rename it away before creating the directory
    if os.path.isfile(path):
        tmp = path + '.old'
        os.rename(path, tmp)
    os.makedirs(path, exist_ok=True)
    return path


def _history_info_path(output_dir: str) -> str:
    return os.path.join(_history_dir(output_dir), 'info')


def _history_thumb_dir(output_dir: str) -> str:
    p = os.path.join(_history_dir(output_dir), 'thumbnails')
    os.makedirs(p, exist_ok=True)
    return p


def _migrate_old_history(output_dir: str) -> None:
    """One-off: move old ``.history`` / ``history`` files into the ``history/`` folder."""
    new_info = _history_info_path(output_dir)

    # Old flat .history or history files
    for old_name in ('.history', '.history.old', 'history'):
        old_path = os.path.join(output_dir, old_name)
        if os.path.isfile(old_path) and not os.path.exists(new_info):
            os.rename(old_path, new_info)
            break

    # Old thumbnails directory at the output root
    old_thumb = os.path.join(output_dir, 'thumbnails')
    new_thumb = os.path.join(_history_dir(output_dir), 'thumbnails')
    if os.path.isdir(old_thumb) and not os.path.isdir(new_thumb):
        try:
            os.rmdir(new_thumb)
        except OSError:
            pass
        os.rename(old_thumb, new_thumb)

    # Migrate from old history/ dir to history/ dir
    old_dir = os.path.join(output_dir, '.history')
    new_dir = os.path.join(output_dir, 'history')
    if os.path.isdir(old_dir) and old_dir != new_dir:
        for item in os.listdir(old_dir):
            old_item = os.path.join(old_dir, item)
            new_item = os.path.join(new_dir, item)
            if not os.path.exists(new_item):
                os.rename(old_item, new_item)
        try:
            os.rmdir(old_dir)
        except OSError:
            pass


def record_history(output_dir: str, /, *, name: str, url: str,
                   total: int, downloaded: int, thumb: str = '') -> None:
    """
    Append one download record to ``<output_dir>/history/info`` (JSON Lines).

    :param thumb: unique thumbnail filename from :func:`save_thumbnail`.
    """
    _migrate_old_history(output_dir)
    info_path = _history_info_path(output_dir)

    record = {
        'name': name,
        'url': url,
        'total': total,
        'downloaded': downloaded,
        'timestamp': datetime.now().astimezone().isoformat(timespec='seconds'),
    }
    if thumb:
        record['thumb'] = thumb

    with open(info_path, 'a', encoding='utf-8') as f:
        f.write(json.dumps(record, ensure_ascii=False) + '\n')


def get_history(output_dir: str) -> list[dict]:
    """
    Read all history records from ``<output_dir>/history/info``.

    Returns a list of dicts (most recent first).  Missing / empty file → ``[]``.
    """
    _migrate_old_history(output_dir)
    info_path = _history_info_path(output_dir)
    if not os.path.exists(info_path):
        return []

    records = []
    with open(info_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    records.reverse()  # newest first
    return records


# ======================================================================
#  Thumbnails  (stored under ``<output_dir>/history/thumbnails/``)
# ======================================================================

def _sanitize_filename(name: str) -> str:
    """Replace characters that are unsafe in filenames (including non-printable ones)."""
    unsafe = '<>:"/\\|?*\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\x0c\x0d\x0e\x0f'
    unsafe += '\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f'
    unsafe += '\xa0'  # non-breaking space
    for ch in unsafe:
        name = name.replace(ch, ' ')
    # Collapse multiple spaces
    import re
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:120]


def save_thumbnail(image: Image.Image, output_dir: str, name: str) -> str:
    """
    Save a small JPEG thumbnail with a unique filename.

    Returns the **base filename** (e.g. ``abc_1a2b3c4d.jpg``) that should be
    stored in the history record's ``thumb`` field.
    """
    thumb_dir = _history_thumb_dir(output_dir)

    thumb = image.copy()
    thumb.thumbnail((320, 480), Image.LANCZOS)

    if thumb.mode in ('RGBA', 'LA', 'P'):
        thumb = thumb.convert('RGB')

    unique = uuid.uuid4().hex[:8]
    fname = _sanitize_filename(name)[:100] + '_' + unique + '.jpg'
    path = os.path.join(thumb_dir, fname)
    thumb.save(path, format='JPEG', quality=75, optimize=True)
    return path  # full path — callers use os.path.basename() for the thumb record field


def _resolve_thumb_path(output_dir: str, record: dict) -> str | None:
    """Return the thumbnail path for a history record, or *None*."""
    thumb_dir = _history_thumb_dir(output_dir)

    # New records have a 'thumb' field with the exact filename
    thumb = record.get('thumb')
    if thumb:
        path = os.path.join(thumb_dir, thumb)
        if os.path.exists(path):
            return path

    # Fallback for old records: derive from name
    path = os.path.join(thumb_dir, _sanitize_filename(record['name']) + '.jpg')
    return path if os.path.exists(path) else None


def get_thumbnail_path(output_dir: str, name: str) -> str | None:
    """Return the path to a saved thumbnail, or *None* if it doesn't exist."""
    path = os.path.join(_history_thumb_dir(output_dir), _sanitize_filename(name) + '.jpg')
    return path if os.path.exists(path) else None


def thumbnail_to_base64(output_dir: str, record: dict) -> str | None:
    """Return the thumbnail for *record* as a base64 data-URI, or *None*."""
    path = _resolve_thumb_path(output_dir, record)
    if not path:
        return None
    import base64
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f'data:image/jpeg;base64,{b64}'


def delete_history_record(output_dir: str, index: int) -> bool:
    """
    Delete one history record (1-based index, newest = 1) and its thumbnail.

    Returns True on success, False if the index is out of range.
    """
    _migrate_old_history(output_dir)
    info_path = _history_info_path(output_dir)
    if not os.path.exists(info_path):
        return False

    # Read all records (oldest-first in file)
    records = []
    with open(info_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    # Convert 1-based newest-first index → position in the file array
    # File order = oldest-first  →  reverse = newest-first
    # index 1 = newest = records[-1]
    # index N = oldest  = records[0]
    if index < 1 or index > len(records):
        return False

    target = records.pop(-index)  # -1 = last = newest

    # Rewrite the info file
    with open(info_path, 'w', encoding='utf-8') as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + '\n')

    # Delete the thumbnail (uses unique thumb field if available)
    thumb_path = _resolve_thumb_path(output_dir, target)
    if thumb_path:
        try:
            os.remove(thumb_path)
        except OSError:
            pass

    return True
