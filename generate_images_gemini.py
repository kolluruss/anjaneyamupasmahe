#!/usr/bin/env python3
"""Generate chapter images using Google Imagen 3 via Gemini API."""

import os
import sys
from pathlib import Path

from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

PROMPTS_DIR = Path("image_prompts")
IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)


def clean_prompt(text: str) -> str:
    """Strip non-ASCII-heavy lines (Telugu footer text)."""
    lines = text.strip().splitlines()
    clean = [l for l in lines if l and sum(1 for c in l if ord(c) > 127) / max(len(l), 1) < 0.5]
    return "\n".join(clean).strip()


def generate_image(chapter_num: int) -> None:
    prompt_file = PROMPTS_DIR / f"chapter-{chapter_num:02d}.txt"
    output_file = IMAGES_DIR / f"chapter-{chapter_num:02d}.png"

    if output_file.exists():
        print(f"  chapter-{chapter_num:02d}: already exists, skipping")
        return

    prompt = clean_prompt(prompt_file.read_text(encoding="utf-8"))

    print(f"  chapter-{chapter_num:02d}: generating...")
    response = client.models.generate_images(
        model="imagen-4.0-generate-001",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            aspect_ratio="1:1",
            safety_filter_level="block_low_and_above",
            person_generation="allow_adult",
        ),
    )

    if not response.generated_images or response.generated_images[0].image is None:
        print(f"  chapter-{chapter_num:02d}: BLOCKED by safety filter")
        return
    image = response.generated_images[0].image
    output_file.write_bytes(image.image_bytes)
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
