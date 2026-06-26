import io
import os
import shutil
import subprocess

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
