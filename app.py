"""Gradio web UI for the Hentai Downloader — runs alongside the terminal version."""
from __future__ import annotations

import base64
import html as _html
import os
import urllib.parse

import gradio as gr
from modules import nhentai
from modules.eromanga import get_images as ero_get_images, scrape_info as ero_scrape_info
from modules.Utils import (
    _sanitize_filename,
    delete_history_record,
    get_history,
    get_file_size_mb,
    record_history,
    save_thumbnail,
    thumbnail_to_base64,
)
from modules.ptf.i2p import I2P

# Port for the inline PDF preview server (separate from Gradio's 7860)
_PREVIEW_PORT = 7861

def _get_lan_ip() -> str:
    """Return the machine's LAN IP, falling back to 127.0.0.1."""
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return '127.0.0.1'

# ---- icon paths ----
_ROOT = os.path.dirname(os.path.abspath(__file__))
_COMICS_ICON = os.path.join(_ROOT, 'comics.icon.webp')
_EROMANGA_ICON = os.path.join(_ROOT, 'eromanga.icon.png')


def _icon_b64(path: str) -> str:
    """Return a base64 data-URI for the icon at *path*."""
    mime = 'image/webp' if path.endswith('.webp') else 'image/png'
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode('ascii')
    return f'data:{mime};base64,{b64}'


# Pre-load icon data URIs
_COMICS_ICON_B64 = _icon_b64(_COMICS_ICON)
_EROMANGA_ICON_B64 = _icon_b64(_EROMANGA_ICON)


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _make_card(record: dict, index: int) -> str:
    """Render one history record as an HTML card with embedded thumbnail + trash button."""
    raw_name = record['name']
    name = _html.escape(raw_name)
    ts = record['timestamp'][:16].replace('T', ' ')
    pages = f"{record['downloaded']}/{record['total']}"
    url = _html.escape(record['url'][:80])

    b64 = thumbnail_to_base64(I2P.output_dir, record)
    if b64:
        thumb_html = (
            f'<img src="{b64}" width="160" '
            f'style="border-radius:6px;object-fit:cover;aspect-ratio:2/3;">'
        )
    else:
        thumb_html = (
            '<div style="width:160px;height:214px;background:#3a3a3a;border-radius:6px;'
            'display:flex;align-items:center;justify-content:center;color:#666;'
            'font-size:0.85em;">No cover</div>'
        )

    # Preview button if the PDF still exists on disk
    safe_name = _sanitize_filename(raw_name)
    pdf_path = os.path.join(I2P.output_dir, f'{safe_name}.pdf')
    preview_btn = ""
    if os.path.isfile(pdf_path):
        encoded = urllib.parse.quote(pdf_path, safe='')
        preview_btn = (
            f'<a href="http://127.0.0.1:{_PREVIEW_PORT}/preview?path={encoded}" '
            f'target="_blank" title="Preview PDF in browser" '
            f'style="position:absolute;bottom:8px;right:64px;color:#888;font-size:14px;'
            f'text-decoration:none;padding:2px 8px;border:1px solid #555;border-radius:4px;'
            f'transition:all 0.15s;" '
            f'onmouseover="this.style.color=\"#fff\";this.style.borderColor=\"#aaa\";" '
            f'onmouseout="this.style.color=\"#888\";this.style.borderColor=\"#555\";">'
            f'Preview</a>'
        )

    return f"""
    <div style="display:flex;gap:16px;padding:12px;border:1px solid #444;
                border-radius:8px;margin-bottom:8px;background:#2b2b2b;position:relative;">
        {thumb_html}
        <div style="flex:1;min-width:0;">
            <h3 style="margin:0 0 6px 0;color:#eee;">{name}</h3>
            <p style="margin:2px 0;color:#aaa;">📅 {ts} &nbsp;|&nbsp; 📄 {pages} pages</p>
            <p style="margin:2px 0;color:#888;font-size:0.85em;overflow:hidden;
                      text-overflow:ellipsis;white-space:nowrap;">🔗 {url}</p>
        </div>
        {preview_btn}
        <span style="position:absolute;bottom:8px;right:8px;color:#666;font-size:14px;"
              title="Select #{{index}} in the delete dropdown below">#{index} 🗑</span>
    </div>"""


def _load_history() -> str:
    """Return all history records rendered as HTML cards (with index for deletion)."""
    records = get_history(I2P.output_dir)
    if not records:
        return "<p style='color:#999;'>No downloads yet.</p>"
    cards = [_make_card(r, i + 1) for i, r in enumerate(records[:50])]
    return '\n'.join(cards)


def _get_delete_choices() -> list[str]:
    """Return dropdown choices for the delete selector."""
    records = get_history(I2P.output_dir)
    return [f"#{i+1}: {r['name'][:60]}" for i, r in enumerate(records[:50])]


def _do_delete(choice: str | None) -> tuple[gr.Dropdown, str, str]:
    """Delete the record selected in the dropdown. Returns (updated_dropdown, status, html)."""
    if not choice:
        return gr.Dropdown(choices=_get_delete_choices()), "⚠ Select a record first.", _load_history()
    try:
        index = int(choice.split(':')[0].lstrip('#'))
    except (ValueError, IndexError):
        return gr.Dropdown(choices=_get_delete_choices()), "⚠ Invalid selection.", _load_history()

    ok = delete_history_record(I2P.output_dir, index)
    if ok:
        new_choices = _get_delete_choices()
        return gr.Dropdown(choices=new_choices, value=None), f"🗑 Deleted {choice.split(':',1)[1].strip() if ':' in choice else choice}", _load_history()
    else:
        return gr.Dropdown(choices=_get_delete_choices()), "⚠ Record not found.", _load_history()


# ---------------------------------------------------------------------------
#  Pipelines
# ---------------------------------------------------------------------------

def _pdf_link(path: str) -> str:
    """Return an HTML button that opens the PDF in a new browser tab."""
    if not path:
        return ""
    encoded = urllib.parse.quote(path, safe='')
    return (
        f'<a href="http://{_get_lan_ip()}:{_PREVIEW_PORT}/preview?path={encoded}" target="_blank" '
        f'style="display:inline-block;padding:8px 20px;background:#2563eb;color:#fff;'
        f'border-radius:6px;text-decoration:none;font-weight:600;">'
        f'Preview PDF in browser</a>'
    )


def _pipeline_hentai_comics(url: str, quality: int, max_dim: int, progress: gr.Progress = gr.Progress()):
    """Download + convert a hentai-comics comic."""

    progress(0.0, desc="Scraping metadata …")
    info = nhentai.scrape_info(url)
    if info is None:
        yield "[X] Failed to scrape metadata.", None, None, ""
        return

    name = info['name']
    total = info['final']
    yield (
        f"**{name}**\n\n"
        f"Pages: {total}  ·  ID: {info['id']}  ·  Format: {info['format']}\n"
        f"CDN: `{info['cdn_base']}`"
    ), None, None, ""

    progress(0.15, desc=f"Downloading {total} pages …")
    images = nhentai.get_images(info)
    if not images:
        yield "[X] No images downloaded.", None, None, ""
        return

    yield f"[OK] Downloaded {len(images)}/{total} pages", None, None, ""
    progress(0.55, desc=f"Compressing {len(images)} images (JPEG q={quality}) …")

    thumb_path = save_thumbnail(images[0], I2P.output_dir, name)

    converter = I2P(images=images, pdf_name=name, is_compress=False,
                    image_quality=quality, max_dimension=max_dim)
    converter.convert_images_to_pdf()
    progress(0.95, desc="Done")

    size_mb = get_file_size_mb(converter.output_file)
    pdf_path = converter.output_file

    record_history(I2P.output_dir, name=name, url=url,
                   total=total, downloaded=len(images),
                   thumb=os.path.basename(thumb_path))

    summary = (
        f"### [OK] Complete\n\n"
        f"**{name}**\n\n"
        f"| | |\n|---|---|\n"
        f"| Pages | {len(images)}/{total} |\n"
        f"| Size | {size_mb:.1f} MB |\n"
        f"| Quality | JPEG {quality} |\n"
        f"| Max dim | {max_dim}px |\n"
    )

    yield summary, pdf_path, thumb_path, _pdf_link(pdf_path)

def _pipeline_eromanga(url: str, quality: int, max_dim: int, progress: gr.Progress = gr.Progress()):
    """Download + convert an eromanga-show.com comic."""

    progress(0.0, desc="Scraping metadata …")
    info = ero_scrape_info(url)
    if info is None:
        yield "[X] Failed to scrape metadata.", None, None, ""
        return

    name = info['name']
    total = info['final']
    yield (
        f"**{name}**\n\n"
        f"Pages: {total}  ·  Article ID: {info['article_id']}"
    ), None, None, ""

    progress(0.15, desc=f"Downloading {total} pages …")
    images = ero_get_images(url)
    if not images:
        yield "[X] No images downloaded.", None, None, ""
        return

    yield f"[OK] Downloaded {len(images)}/{total} pages", None, None, ""
    progress(0.55, desc=f"Compressing {len(images)} images (JPEG q={quality}) …")

    thumb_path = save_thumbnail(images[0], I2P.output_dir, name)

    converter = I2P(images=images, pdf_name=name, is_compress=False,
                    image_quality=quality, max_dimension=max_dim)
    converter.convert_images_to_pdf()
    progress(0.95, desc="Done")

    size_mb = get_file_size_mb(converter.output_file)
    pdf_path = converter.output_file

    record_history(I2P.output_dir, name=name, url=url,
                   total=total, downloaded=len(images),
                   thumb=os.path.basename(thumb_path))

    summary = (
        f"### [OK] Complete\n\n"
        f"**{name}**\n\n"
        f"| | |\n|---|---|\n"
        f"| Pages | {len(images)}/{total} |\n"
        f"| Size | {size_mb:.1f} MB |\n"
        f"| Quality | JPEG {quality} |\n"
        f"| Max dim | {max_dim}px |\n"
    )

    yield summary, pdf_path, thumb_path, _pdf_link(pdf_path)

# ---------------------------------------------------------------------------
#  UI layout
# ---------------------------------------------------------------------------

def _build_download_tab(placeholder: str, info: str, pipeline_fn,
                        history_html: gr.HTML, del_dropdown: gr.Dropdown):
    """Build the shared layout for a download tab."""
    url_input = gr.Textbox(
        label="URL",
        placeholder=placeholder,
        info=info,
    )
    with gr.Row():
        quality_slider = gr.Slider(
            minimum=30, maximum=95, value=60, step=5,
            label="JPEG Quality",
            info="60 = aggressive; 85 = balanced; 95 = near-lossless",
            scale=1,
        )
        max_dim_dropdown = gr.Dropdown(
            choices=[("1080p (aggressive)", 1080), ("1600p (default)", 1600),
                     ("Original (no resize)", 0), ("720p (tiny)", 720)],
            value=1600, label="Max Resolution",
            info="Downsample images to this height",
            scale=1,
        )

    run_btn = gr.Button("🚀 Download", variant="primary", size="lg")

    with gr.Row():
        with gr.Column(scale=2):
            status_text = gr.Markdown("")
            pdf_output = gr.File(label="📄 PDF (download)")
            preview_link = gr.HTML("")
        with gr.Column(scale=1):
            cover_image = gr.Image(label="🖼 Cover")

    run_btn.click(
        fn=pipeline_fn,
        inputs=[url_input, quality_slider, max_dim_dropdown],
        outputs=[status_text, pdf_output, cover_image, preview_link],
    )
    # After download completes, refresh history
    run_btn.click(
        fn=lambda: (_load_history(), gr.Dropdown(choices=_get_delete_choices(), value=None)),
        outputs=[history_html, del_dropdown],
    )


def build_ui():
    with gr.Blocks(title="Hentai Downloader") as app:
        gr.Markdown("Hentai Downloader")
        gr.Markdown("Paste a comic URL, click download, get a PDF.")

        # History tab first (for component creation / cross-tab sync),
        # CSS in _HEAD moves it visually to the end
        with gr.Tab("History"):
            history_html = gr.HTML(_load_history())
            with gr.Row():
                history_btn = gr.Button("🔄 Refresh")
                del_dropdown = gr.Dropdown(
                    label="Select record to delete",
                    choices=_get_delete_choices(),
                    value=None,
                    scale=2,
                )
                del_btn = gr.Button("🗑 Delete", variant="stop", size="sm")
            del_status = gr.Markdown("")
            del_btn.click(
                fn=_do_delete,
                inputs=[del_dropdown],
                outputs=[del_dropdown, del_status, history_html],
            )
            history_btn.click(
                fn=lambda: (_load_history(), gr.Dropdown(choices=_get_delete_choices(), value=None)),
                outputs=[history_html, del_dropdown],
            )

        with gr.Tab("hentai-comics"):
            _build_download_tab(
                placeholder="https://nhentai.com/en/comic/…",
                info="Browse comics at https://nhentai.com/hentai-comics",
                pipeline_fn=_pipeline_hentai_comics,
                history_html=history_html,
                del_dropdown=del_dropdown,
            )

        with gr.Tab("eromanga"):
            _build_download_tab(
                placeholder="https://eromanga-show.com/articles/…",
                info="Browse comics at https://eromanga-show.com",
                pipeline_fn=_pipeline_eromanga,
                history_html=history_html,
                del_dropdown=del_dropdown,
            )

        gr.Markdown("---\n*Terminal version: `python main.py`*")

    return app


def _start_preview_server(port: int = _PREVIEW_PORT):
    """Start a tiny HTTP server on *port* that serves PDFs with inline Content-Disposition."""
    import threading
    from http.server import HTTPServer, SimpleHTTPRequestHandler

    class PreviewHandler(SimpleHTTPRequestHandler):
        def do_GET(self):
            from urllib.parse import parse_qs, urlparse, unquote
            qs = parse_qs(urlparse(self.path).query)
            file_path = unquote(qs.get('path', [''])[0])
            if os.path.isfile(file_path) and file_path.lower().endswith('.pdf'):
                self.send_response(200)
                self.send_header('Content-Type', 'application/pdf')
                # RFC 5987: encode non-ASCII filename for Content-Disposition
                fname = os.path.basename(file_path)
                try:
                    fname.encode('latin-1')
                except UnicodeEncodeError:
                    from urllib.parse import quote
                    fname = f"UTF-8''{quote(fname)}"
                self.send_header('Content-Disposition', f'inline; filename={fname}')
                self.send_header('Content-Length', str(os.path.getsize(file_path)))
                self.end_headers()
                with open(file_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, 'File not found')

        def log_message(self, format, *args):
            pass  # suppress logs

    server = HTTPServer(('0.0.0.0', port), PreviewHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


if __name__ == '__main__':
    _start_preview_server()

    # CSS injected into the page <head>
    _HEAD = f"""
    <style>
        /* night color scheme */
        html {{ color-scheme: dark; }}
        /* visually reorder tabs: History → last */
        .tab-nav {{ display: flex; }}
        .tab-nav button[role="tab"]:nth-of-type(1) {{ order: 3; }}
        .tab-nav button[role="tab"]:nth-of-type(2) {{ order: 1; }}
        .tab-nav button[role="tab"]:nth-of-type(3) {{ order: 2; }}
        /* tab icons (DOM order: History, hentai-comics, eromanga) */
        button[role="tab"]:nth-of-type(2)::before {{
            content: "";
            display: inline-block;
            width: 22px; height: 22px;
            background: url({_COMICS_ICON_B64}) center / contain no-repeat;
            vertical-align: middle;
            margin-right: 6px;
            flex-shrink: 0;
            border-radius: 3px;
        }}
        button[role="tab"]:nth-of-type(3)::before {{
            content: "";
            display: inline-block;
            width: 22px; height: 22px;
            background: url({_EROMANGA_ICON_B64}) center / contain no-repeat;
            vertical-align: middle;
            margin-right: 6px;
            flex-shrink: 0;
            border-radius: 3px;
        }}
    </style>
    """
    demo = build_ui()

    lan_ip = _get_lan_ip()
    print(f"LAN access: http://{lan_ip}:7860")
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        inbrowser=True,
        head=_HEAD,
    )
