#!/usr/bin/env python3.9
"""
make_book.py  —  ఆంజనేయముపాస్మహే: all chapters → PDF (A4 and/or Demy)

HOW TO RUN
----------
  cd /path/to/anjaneyamupasmahe
  python3.9 publishing/make_book.py                 # builds both A4 and Demy PDFs
  python3.9 publishing/make_book.py --size a4       # A4 only
  python3.9 publishing/make_book.py --size demy     # Demy only
  python3.9 publishing/make_book.py --no-download   # skip Google Drive image sync
  python3.9 publishing/make_book.py --force-download # re-download all images

OUTPUT
------
  pdfs/anjaneyamupasmahe_a4.pdf
  pdfs/anjaneyamupasmahe_demy.pdf
"""

import re
import shutil
import platform
import subprocess
import urllib.request
from pathlib import Path

BASE      = Path(__file__).resolve().parent.parent
CHAP_DIR  = BASE / "chapters"
IMG_DIR   = BASE / "images"
CSS_FILE  = BASE / "publishing" / "book.css"
FONTS_DIR = BASE / "publishing" / "fonts_cache"
OUTPUT_DIR = BASE / "pdfs"

# page_size, margin (top right bottom left), output filename, label
SIZE_CONFIGS = {
    "a4": {
        "page_size": "8.27in 11.69in",
        "margin":    "0.9in 0.8in 1.25in 1.1in",
        "output":    "anjaneyamupasmahe_a4.pdf",
        "preview":   "anjaneyamupasmahe_a4_preview.html",
        "label":     "A4",
    },
    "demy": {
        "page_size": "5.5in 8.5in",
        "margin":    "0.75in 0.65in 1.1in 0.9in",
        "output":    "anjaneyamupasmahe_demy.pdf",
        "preview":   "anjaneyamupasmahe_demy_preview.html",
        "label":     "Demy (5.5″ × 8.5″)",
    },
}

GDRIVE_FOLDER_ID = "1OPsgJ85Ri4sJ8wkHJzZUXv0bGfzQQVyT"  # images source on Google Drive

FONT_URLS = {
    "Ponnala.ttf": "https://fonts.gstatic.com/s/ponnala/v3/w8gaH2QxQOU08bbbrQs.ttf",
    "Gidugu.ttf":  "https://fonts.gstatic.com/s/gidugu/v21/L0x8DFMkk1Sn6gFLJBKv.ttf",
}


# ── Font installation ─────────────────────────────────────────────

def _system_font_dir() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Fonts"
    return Path.home() / ".fonts"


def _install_system_font(src: Path) -> bool:
    dest_dir = _system_font_dir()
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not dest.exists():
        shutil.copy2(src, dest)
        print(f"  Installed {src.name} → {dest_dir}", flush=True)
        return True
    return False


def ensure_fonts():
    FONTS_DIR.mkdir(exist_ok=True)
    any_new = False
    for fname, url in FONT_URLS.items():
        fp = FONTS_DIR / fname
        if not fp.exists():
            print(f"  Downloading {fname}…", flush=True)
            urllib.request.urlretrieve(url, fp)
        any_new |= _install_system_font(fp)
    if any_new and platform.system() != "Darwin":
        subprocess.run(["fc-cache", "-fv", str(_system_font_dir())], capture_output=True)
    print("  Fonts ready.")


def font_face_css() -> str:
    def uri(name):
        return (FONTS_DIR / name).as_uri()
    return f"""
@font-face {{
  font-family: 'Ponnala';
  src: url('{uri("Ponnala.ttf")}') format('truetype');
  font-weight: normal; font-style: normal;
}}
@font-face {{
  font-family: 'Gidugu';
  src: url('{uri("Gidugu.ttf")}') format('truetype');
  font-weight: normal; font-style: normal;
}}
"""


def dynamic_page_css(page_size: str, margin: str) -> str:
    """Override @page with the correct size and margins for this build."""
    return f"""
{font_face_css()}
@page cover-pg {{ size: {page_size}; margin: 0; }}
@page {{
  size: {page_size};
  margin: {margin};
  @bottom-left {{
    content: "ఆంజనేయముపాస్మహే";
    font-family: 'Gidugu', sans-serif;
    font-size: 8pt;
    color: #888;
    border-top: 0.5pt solid #ccc;
    padding-top: 4pt;
  }}
  @bottom-right {{
    content: counter(page);
    font-family: 'Gidugu', sans-serif;
    font-size: 8pt;
    color: #888;
    border-top: 0.5pt solid #ccc;
    padding-top: 4pt;
  }}
}}
"""


# ── Chapter sorting ───────────────────────────────────────────────

def chap_sort_key(path: Path):
    """Sort by chapter number; named sub-chapters (e.g. 'foreword') sort before numbered ones."""
    stem = path.stem
    m = re.match(r'chapter-(\d+)(?:-(.+))?$', stem)
    if not m:
        return (999, 0, stem)
    major = int(m.group(1))
    rest  = m.group(2) or ''
    num_m = re.match(r'^(\d+)', rest)
    if num_m:
        minor = int(num_m.group(1))
    elif rest == '':
        minor = 0
    else:
        minor = -1   # text suffix (e.g. 'foreword') before numbered sub-chapters
    return (major, minor, rest)


# ── Markdown pre-processing ───────────────────────────────────────

def preprocess_markdown(text: str) -> str:
    """Fix image paths and strip unresolvable placeholders from Google Docs exports."""
    text = re.sub(r'!\[([^\]]*)\]\(\.\./images/', r'![\1](images/', text)
    text = re.sub(r'!\[\]\[image\d+\]', '', text)
    return text


# ── Markdown → HTML ───────────────────────────────────────────────

def chapter_to_html(path: Path, is_first: bool) -> str:
    import markdown as md_lib
    text = path.read_text(encoding='utf-8')
    text = preprocess_markdown(text)
    converter = md_lib.Markdown(extensions=['extra'])
    body = converter.convert(text)
    cls  = 'chapter first-chapter' if is_first else 'chapter'
    return f'<div class="{cls}">\n{body}\n</div>\n'


# ── Google Drive image sync ───────────────────────────────────────

def _ensure_packages(*packages):
    import sys
    _pkg_imports = {
        "google-api-python-client": "googleapiclient",
    }
    for pkg in packages:
        import_name = _pkg_imports.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            print(f"  Installing {pkg}…", flush=True)
            subprocess.run([sys.executable, "-m", "pip", "install", pkg, "-q"])


def sync_images_from_gdrive(force: bool = False):
    """Download all images from the Google Drive folder into images/.
    Requires GOOGLE_API_KEY env var; the Drive folder must be shared as
    'Anyone with the link' (Viewer).
    """
    import os
    existing = list(IMG_DIR.glob("*.png"))
    if existing and not force:
        print(f"  Images cached: {len(existing)} files in {IMG_DIR}")
        return

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print("  WARNING: GOOGLE_API_KEY not set — skipping image download")
        return

    _ensure_packages("google-api-python-client")
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    import io

    IMG_DIR.mkdir(exist_ok=True)
    service = build("drive", "v3", developerKey=api_key)

    print(f"  Downloading images from Drive folder {GDRIVE_FOLDER_ID}…", flush=True)
    files, page_token = [], None
    while True:
        resp = service.files().list(
            q=f"'{GDRIVE_FOLDER_ID}' in parents and trashed=false",
            fields="nextPageToken, files(id, name)",
            pageSize=1000,
            pageToken=page_token,
        ).execute()
        files.extend(resp.get("files", []))
        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    pngs = [f for f in files if f["name"].endswith(".png")]
    print(f"  Found {len(pngs)} images", flush=True)
    for f in pngs:
        dest = IMG_DIR / f["name"]
        req  = service.files().get_media(fileId=f["id"])
        buf  = io.FileIO(dest, mode="wb")
        dl   = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = dl.next_chunk()
        print(f"    {f['name']}", flush=True)
    print(f"  Downloaded {len(pngs)} images.")


# ── Main ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build ఆంజనేయముపాస్మహే PDF")
    parser.add_argument(
        "--size", choices=["a4", "demy", "both"], default="both",
        help="Page size to build (default: both)",
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="Skip Google Drive image download (use locally cached images)"
    )
    parser.add_argument(
        "--force-download", action="store_true",
        help="Re-download images from Google Drive even if already cached"
    )
    args = parser.parse_args()

    sizes = ["a4", "demy"] if args.size == "both" else [args.size]

    print("Checking fonts…")
    ensure_fonts()

    if not args.no_download:
        print("Syncing images…")
        sync_images_from_gdrive(force=args.force_download)

    chap_files = sorted(CHAP_DIR.glob("chapter-*.md"), key=chap_sort_key)
    print(f"Found {len(chap_files)} chapter files")

    bodies = []
    for i, f in enumerate(chap_files):
        bodies.append(chapter_to_html(f, is_first=(i == 0)))
        print(f"  {f.name}")

    body_html = ''.join(bodies)
    OUTPUT_DIR.mkdir(exist_ok=True)

    from weasyprint import HTML as WP, CSS

    for size_key in sizes:
        cfg = SIZE_CONFIGS[size_key]
        dyn_css = dynamic_page_css(cfg["page_size"], cfg["margin"])

        cover_front = IMG_DIR / 'cover_front.png'
        front_html  = (f'<div class="cover-pg">'
                       f'<img src="{cover_front.as_uri()}" alt="front cover">'
                       f'</div>') if cover_front.exists() else ''

        html = f"""<!DOCTYPE html>
<html lang="te">
<head>
  <meta charset="UTF-8">
  <title>ఆంజనేయముపాస్మహే</title>
  <style>{dyn_css}</style>
</head>
<body>
{front_html}
{body_html}
</body>
</html>"""

        preview_path = OUTPUT_DIR / cfg["preview"]
        preview_path.write_text(html, encoding="utf-8")
        print(f"Preview  : {preview_path}")

        output_path = OUTPUT_DIR / cfg["output"]
        print(f"Generating PDF ({cfg['label']})…")
        stylesheets = [
            CSS(filename=str(CSS_FILE)),
            CSS(string=dyn_css),
        ]
        WP(string=html, base_url=str(BASE)).write_pdf(
            str(output_path), stylesheets=stylesheets
        )
        size_mb = output_path.stat().st_size / 1024 / 1024
        print(f"Done     : {output_path}  ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
