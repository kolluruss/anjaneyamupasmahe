#!/usr/bin/env python3
"""Generate chapter images using OpenAI gpt-image-1."""

import os
import base64
import sys
from pathlib import Path

from openai import OpenAI

client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

PROMPTS_DIR = Path("image_prompts")
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

def generate_image(chapter_num: int) -> None:
    prompt_file = PROMPTS_DIR / f"chapter-{chapter_num:02d}.txt"
    output_file = IMAGES_DIR / f"chapter-{chapter_num:02d}.png"

    if output_file.exists():
        print(f"  chapter-{chapter_num:02d}: already exists, skipping")
        return

    prompt = prompt_file.read_text(encoding="utf-8").strip()
    # Trim any Telugu footer text (non-ASCII heavy paragraphs at end)
    lines = prompt.splitlines()
    ascii_lines = [l for l in lines if l and sum(1 for c in l if ord(c) > 127) / max(len(l), 1) < 0.5]
    clean_prompt = "\n".join(ascii_lines).strip()

    print(f"  chapter-{chapter_num:02d}: generating...")
    response = client.images.generate(
        model="gpt-image-1",
        prompt=clean_prompt,
        size="1024x1024",
        quality="high",
        n=1,
    )

    image_data = response.data[0].b64_json
    image_bytes = base64.b64decode(image_data)
    output_file.write_bytes(image_bytes)
    print(f"  chapter-{chapter_num:02d}: saved to {output_file}")


def main():
    chapters = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else list(range(1, 6))
    print(f"Generating images for chapters: {chapters}")
    for ch in chapters:
        try:
            generate_image(ch)
        except Exception as e:
            print(f"  chapter-{ch:02d}: ERROR - {e}")


if __name__ == "__main__":
    main()
