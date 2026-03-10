#!/usr/bin/env python3
"""
O&G + Mining Intelligence Brief — Audio Generator
Extracts text from edition HTML and generates MP3 using Microsoft Neural TTS.
Requires: pip install edge-tts beautifulsoup4
"""

import asyncio
import sys
import os
import re
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("Install edge-tts: pip install edge-tts")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    # Fallback: use regex-based extraction
    BeautifulSoup = None

# Voice config
VOICE = "pt-BR-FranciscaNeural"
RATE = "+5%"  # Slightly faster than default

# Elements to skip when extracting text
SKIP_CLASSES = [
    'source', 'calendar-btn', 'back-link', 'listen-btn',
    'subscribe-form', 'subscribe-card'
]
SKIP_TAGS = ['script', 'style', 'button']

# Emoji/symbol cleanup
SYMBOLS_RE = re.compile(
    r'[\u2693\u26BD\u26A1\U0001F30D\U0001F4CA\U0001F4CB\U0001F3AF'
    r'\U0001F9E0\U0001F4C8\U0001F5C2\U0001F4DA\U0001F6A8\u2694\U0001F52E'
    r'\U0001F1E7\U0001F1F7\U0001F4A1\u25B8\u25B2\u25BC\u25CF\u25C6'
    r'\u2197\U0001F4C5\U0001F6E2\u26A0\U0001F3ED\u2696\U0001F4F0'
    r'\U0001F50B\U0001F4B0\U0001F3D7\U0001F50D\U0001F454\U0001F393'
    r'\U0001F3E2\u23F0\U0001F4CC\u26FD\u26CF\U0001F525]+', re.UNICODE
)


def extract_text_bs4(html_path):
    """Extract readable text using BeautifulSoup."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    container = soup.find(class_='container')
    if not container:
        container = soup.find('body')

    # Remove unwanted elements
    for cls in SKIP_CLASSES:
        for el in container.find_all(class_=cls):
            el.decompose()
    for tag in SKIP_TAGS:
        for el in container.find_all(tag):
            el.decompose()

    text = container.get_text(separator=' ')
    text = SYMBOLS_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_text_regex(html_path):
    """Fallback text extraction using regex."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    # Remove script/style tags
    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', ' ', html)
    # Decode entities
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#8592;', '').replace('&times;', '')
    # Clean symbols
    text = SYMBOLS_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_text(html_path):
    """Extract text from HTML edition file."""
    if BeautifulSoup:
        return extract_text_bs4(html_path)
    return extract_text_regex(html_path)


async def generate_audio(text, output_path, voice=VOICE, rate=RATE):
    """Generate MP3 from text using edge-tts."""
    # Add intro
    intro = "Voce esta ouvindo o O and G plus Mining Intelligence Brief. "
    full_text = intro + text

    # Add closing
    full_text += " Fim da edicao. Obrigado por ouvir."

    print(f"Generating audio ({len(full_text)} chars)...")
    print(f"Voice: {voice}")
    print(f"Output: {output_path}")

    comm = edge_tts.Communicate(full_text, voice, rate=rate)
    await comm.save(str(output_path))

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Done! File size: {size_mb:.1f} MB")


def main():
    if len(sys.argv) < 2:
        print("Usage: python generate-audio.py <edition.html> [output.mp3]")
        print("Example: python generate-audio.py editions/2026-03-10.html")
        sys.exit(1)

    html_path = Path(sys.argv[1])
    if not html_path.exists():
        print(f"File not found: {html_path}")
        sys.exit(1)

    # Default output: same name but .mp3
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])
    else:
        output_path = html_path.with_suffix('.mp3')

    text = extract_text(html_path)
    if len(text) < 100:
        print("Warning: very little text extracted. Check HTML structure.")

    print(f"Extracted {len(text)} characters from {html_path.name}")

    asyncio.run(generate_audio(text, output_path))


if __name__ == '__main__':
    main()
