# ERO-Downloader

Download doujinshi from nhentai.com and eromanga-show.com, package as PDF. Includes a Gradio web UI and terminal CLI.

## Installation

```bash
git clone --recurse-submodules https://github.com/Akisamu/ERO-Downloader.git
cd ERO-Downloader
python -m venv .venv
source .venv/bin/activate       # Linux / macOS
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
```

Optional: install [Ghostscript](https://ghostscript.com/) for additional PDF post-compression.

## Usage

### Web UI (recommended)

```bash
python app.py
# Opens http://127.0.0.1:7860
# LAN devices: http://<your-ip>:7860
```

Three tabs:

| Tab | Purpose |
|-----|---------|
| hentai-comics | Paste a nhentai.com comic URL — auto-scrapes metadata, downloads images, generates PDF |
| eromanga | Paste an eromanga-show.com article URL — same pipeline |
| History | Download log with thumbnail previews, inline PDF viewer, per-record delete |

Adjustable JPEG quality (30–95) and max resolution (720p / 1080p / 1600p / original).

### Terminal mode

Edit the URL lists in `main.py`, then run:

```bash
python main.py
```

Three input modes:

```python
# Mode A — nhentai.com URLs (auto-scrape)
nhentai_urls = ['https://nhentai.com/en/comic/...']

# Mode B — eromanga-show.com article URLs (auto-scrape)
eromanga_urls = ['https://eromanga-show.com/articles/...']

# Mode C — manual metadata
infos = [{'name': '...', 'final': 70, 'id': 616696, 'format': 'webp'}]
```

## Output structure

```
outputs/
  .history/
    info              ← download log (JSON Lines)
    thumbnails/       ← cover thumbnails
  *.pdf               ← generated PDFs
```

## Dependencies

`beautifulsoup4` `gradio` `natsort` `pillow` `reportlab` `requests` `tqdm`

## License

[MIT](LICENSE)
