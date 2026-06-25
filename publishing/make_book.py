#!/usr/bin/env python3.9
"""
make_book.py  —  ఆంజనేయముపాస్మహే: all chapters → single PDF

HOW TO RUN
----------
  cd /path/to/anjaneyamupasmahe
  python3.9 publishing/make_book.py                 # generates PDF
  python3.9 publishing/make_book.py --upload-drive  # also upload to Google Drive

OUTPUT
------
  pdfs/anjaneyamupasmahe.pdf
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
OUTPUT    = BASE / "pdfs" / "anjaneyamupasmahe.pdf"
PREVIEW   = BASE / "pdfs" / "anjaneyamupasmahe-preview.html"
CSS_FILE  = BASE / "publishing" / "book.css"
FONTS_DIR = BASE / "publishing" / "fonts_cache"

GDRIVE_PDF_FOLDER_ID = ""   # fill in before using --upload-drive
GDRIVE_CREDS_FILE    = BASE / "publishing" / "gdrive_credentials.json"
GDRIVE_TOKEN_FILE    = BASE / "publishing" / "gdrive_token.json"

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


# ── Google Drive upload ───────────────────────────────────────────

_GOOGLE_PKG_IMPORTS = {
    "google-auth":              "google.auth",
    "google-auth-oauthlib":     "google_auth_oauthlib",
    "google-auth-httplib2":     "google_auth_httplib2",
    "google-api-python-client": "googleapiclient",
}


def _ensure_packages(*packages):
    import sys
    for pkg in packages:
        import_name = _GOOGLE_PKG_IMPORTS.get(pkg, pkg.replace("-", "_"))
        try:
            __import__(import_name)
        except ImportError:
            print(f"Installing {pkg}…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])


def get_drive_service():
    import os
    _ensure_packages(
        "google-auth", "google-auth-oauthlib",
        "google-auth-httplib2", "google-api-python-client",
    )
    from googleapiclient.discovery import build
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    refresh_token = os.environ.get("GDRIVE_REFRESH_TOKEN")
    client_id     = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if refresh_token and client_id and client_secret:
        creds = Credentials(
            token=None, refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id, client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/drive"],
        )
        creds.refresh(Request())
        return build("drive", "v3", credentials=creds)

    from google_auth_oauthlib.flow import InstalledAppFlow
    SCOPES = ["https://www.googleapis.com/auth/drive"]
    creds  = None
    if GDRIVE_TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(GDRIVE_TOKEN_FILE), SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not GDRIVE_CREDS_FILE.exists():
                raise FileNotFoundError(
                    "\nNo Drive credentials found. Either:\n"
                    "  Set GDRIVE_REFRESH_TOKEN + GOOGLE_CLIENT_ID + GOOGLE_CLIENT_SECRET\n"
                    "  Or place OAuth2 Desktop credentials at publishing/gdrive_credentials.json\n"
                )
            flow  = InstalledAppFlow.from_client_secrets_file(str(GDRIVE_CREDS_FILE), SCOPES)
            creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
        GDRIVE_TOKEN_FILE.write_text(creds.to_json())
    return build("drive", "v3", credentials=creds)


def upload_pdf_to_gdrive(pdf_path: Path) -> str:
    if not GDRIVE_PDF_FOLDER_ID:
        print("  GDRIVE_PDF_FOLDER_ID not set in make_book.py — skipping upload.")
        return ""
    from googleapiclient.http import MediaFileUpload
    service = get_drive_service()
    media   = MediaFileUpload(str(pdf_path), mimetype="application/pdf", resumable=True)
    existing = service.files().list(
        q=(f"name='{pdf_path.name}' and '{GDRIVE_PDF_FOLDER_ID}' in parents and trashed=false"),
        fields="files(id, name)",
        supportsAllDrives=True, includeItemsFromAllDrives=True,
    ).execute().get("files", [])
    if existing:
        file_id = existing[0]["id"]
        service.files().update(fileId=file_id, media_body=media, supportsAllDrives=True).execute()
        print(f"  Updated in Drive : {pdf_path.name}")
    else:
        meta   = {"name": pdf_path.name, "parents": [GDRIVE_PDF_FOLDER_ID]}
        result = service.files().create(
            body=meta, media_body=media, fields="id", supportsAllDrives=True
        ).execute()
        file_id = result["id"]
        print(f"  Uploaded to Drive: {pdf_path.name}")
    url = f"https://drive.google.com/file/d/{file_id}/view"
    print(f"  URL: {url}")
    return url


# ── Main ─────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build ఆంజనేయముపాస్మహే PDF")
    parser.add_argument("--upload-drive", action="store_true",
                        help="Upload generated PDF to Google Drive")
    args = parser.parse_args()

    print("Checking fonts…")
    ensure_fonts()

    chap_files = sorted(CHAP_DIR.glob("chapter-*.md"), key=chap_sort_key)
    print(f"Found {len(chap_files)} chapter files")

    bodies = []
    for i, f in enumerate(chap_files):
        bodies.append(chapter_to_html(f, is_first=(i == 0)))
        print(f"  {f.name}")

    html = f"""<!DOCTYPE html>
<html lang="te">
<head>
  <meta charset="UTF-8">
  <title>ఆంజనేయముపాస్మహే</title>
  <link rel="stylesheet" href="../publishing/book.css">
  <style>{font_face_css()}</style>
</head>
<body>
{''.join(bodies)}
</body>
</html>"""

    PREVIEW.parent.mkdir(exist_ok=True)
    PREVIEW.write_text(html, encoding="utf-8")
    print(f"Preview  : {PREVIEW}")

    print("Generating PDF…")
    from weasyprint import HTML as WP, CSS
    OUTPUT.parent.mkdir(exist_ok=True)
    stylesheet = CSS(filename=str(CSS_FILE))
    WP(string=html, base_url=str(BASE)).write_pdf(str(OUTPUT), stylesheets=[stylesheet])
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"Done     : {OUTPUT}  ({size_mb:.1f} MB)")

    if args.upload_drive:
        print("Uploading to Google Drive…")
        upload_pdf_to_gdrive(OUTPUT)


if __name__ == "__main__":
    main()
