#!/usr/bin/env python3.9
"""
get_gdrive_secrets.py — Print env vars needed for local --upload-drive use.

Run this after authenticating once locally:
  python3.9 publishing/make_book.py --upload-drive   # opens browser on first run
  python3.9 publishing/get_gdrive_secrets.py         # prints the token values
"""

import json, sys
from pathlib import Path

BASE       = Path(__file__).resolve().parent.parent
token_file = BASE / "publishing" / "gdrive_token.json"
creds_file = BASE / "publishing" / "gdrive_credentials.json"

if not token_file.exists():
    print("ERROR: No token found.")
    print("Run: python3.9 publishing/make_book.py --upload-drive")
    print("A browser will open for a one-time login and cache the token.")
    sys.exit(1)

token = json.loads(token_file.read_text())

client_id     = token.get("client_id", "")
client_secret = token.get("client_secret", "")
refresh_token = token.get("refresh_token", "")

if (not client_id or not client_secret) and creds_file.exists():
    installed     = json.loads(creds_file.read_text()).get("installed", {})
    client_id     = client_id     or installed.get("client_id", "")
    client_secret = client_secret or installed.get("client_secret", "")

missing = [k for k, v in {
    "client_id":     client_id,
    "client_secret": client_secret,
    "refresh_token": refresh_token,
}.items() if not v]

if missing:
    print(f"ERROR: Could not find: {', '.join(missing)}")
    print("Re-run: python3.9 publishing/make_book.py --upload-drive")
    sys.exit(1)

print("\n" + "="*60)
print("Env vars for --upload-drive without a browser:")
print("="*60)
print(f"\nexport GOOGLE_CLIENT_ID={client_id}")
print(f"export GOOGLE_CLIENT_SECRET={client_secret}")
print(f"export GDRIVE_REFRESH_TOKEN={refresh_token}")
print("\n" + "="*60 + "\n")
