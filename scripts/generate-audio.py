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
    BeautifulSoup = None

# Voice config
VOICE = "pt-BR-FranciscaNeural"
RATE = "-3%"  # Slightly slower for natural pacing

# Elements to SKIP in audio (not narrative text)
SKIP_CLASSES = [
    # Navigation and UI
    'source', 'calendar-btn', 'back-link', 'listen-btn',
    'subscribe-form', 'subscribe-card',
    # Number indicators and stats (legacy)
    'numbers-grid', 'num-card', 'stats-bar', 'stat-item',
    'scenario-grid', 'scenario-card', 'player-meta',
    'section-divider', 'tags', 'impact', 'change',
    'header-meta', 'header-icon', 'footer',
    # Market ticker (new format — prices don't sound good in audio)
    'market-ticker', 'ticker-grid', 'ticker-item',
    'ticker-symbol', 'ticker-price', 'ticker-change',
    # Agenda/calendar section (dates and event metadata)
    'agenda-section', 'agenda-item', 'agenda-date-badge',
    'agenda-day', 'agenda-month', 'agenda-info',
    'agenda-title', 'agenda-org', 'agenda-desc',
    # Executive summary (bullet points sound bad in audio)
    'exec-summary',
    # Sources/references (irrelevant in audio)
    'source',
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

# ============================================================
# Abbreviation expansion for natural speech
# ============================================================
ABBREVIATIONS = [
    # Months (standalone or after day numbers)
    (r'\b(\d{1,2})\s*/\s*mar\b', r'\1 de março'),
    (r'\b(\d{1,2})\s*/\s*fev\b', r'\1 de fevereiro'),
    (r'\b(\d{1,2})\s*/\s*jan\b', r'\1 de janeiro'),
    (r'\b(\d{1,2})\s*/\s*abr\b', r'\1 de abril'),
    (r'\b(\d{1,2})\s*/\s*mai\b', r'\1 de maio'),
    (r'\b(\d{1,2})\s*/\s*jun\b', r'\1 de junho'),
    (r'\b(\d{1,2})\s*/\s*jul\b', r'\1 de julho'),
    (r'\b(\d{1,2})\s*/\s*ago\b', r'\1 de agosto'),
    (r'\b(\d{1,2})\s*/\s*set\b', r'\1 de setembro'),
    (r'\b(\d{1,2})\s*/\s*out\b', r'\1 de outubro'),
    (r'\b(\d{1,2})\s*/\s*nov\b', r'\1 de novembro'),
    (r'\b(\d{1,2})\s*/\s*dez\b', r'\1 de dezembro'),
    # "10 Mar 2026" format
    (r'\b(\d{1,2})\s+[Mm]ar\s+(\d{4})', r'\1 de março de \2'),
    (r'\b(\d{1,2})\s+[Ff]ev\s+(\d{4})', r'\1 de fevereiro de \2'),
    (r'\b(\d{1,2})\s+[Jj]an\s+(\d{4})', r'\1 de janeiro de \2'),
    (r'\b(\d{1,2})\s+[Aa]br\s+(\d{4})', r'\1 de abril de \2'),
    (r'\b(\d{1,2})\s+[Mm]ai\s+(\d{4})', r'\1 de maio de \2'),
    (r'\b(\d{1,2})\s+[Jj]un\s+(\d{4})', r'\1 de junho de \2'),
    (r'\b(\d{1,2})\s+[Jj]ul\s+(\d{4})', r'\1 de julho de \2'),
    (r'\b(\d{1,2})\s+[Aa]go\s+(\d{4})', r'\1 de agosto de \2'),
    (r'\b(\d{1,2})\s+[Ss]et\s+(\d{4})', r'\1 de setembro de \2'),
    (r'\b(\d{1,2})\s+[Oo]ut\s+(\d{4})', r'\1 de outubro de \2'),
    (r'\b(\d{1,2})\s+[Nn]ov\s+(\d{4})', r'\1 de novembro de \2'),
    (r'\b(\d{1,2})\s+[Dd]ez\s+(\d{4})', r'\1 de dezembro de \2'),

    # Units - oil & gas
    (r'Mb/d', 'milhões de barris por dia'),
    (r'Mboe/d', 'milhões de barris de óleo equivalente por dia'),
    (r'bbl', 'barris'),
    (r'b/d', 'barris por dia'),

    # Units - energy
    (r'\bGW\b', 'gigawatts'),
    (r'\bMW\b', 'megawatts'),
    (r'\bTWh\b', 'terawatt-hora'),
    (r'\bGWh\b', 'gigawatt-hora'),
    (r'\bMWh\b', 'megawatt-hora'),

    # Currency and numbers
    (r'US\$\s*', 'dólares '),
    (r'R\$\s*', 'reais '),
    (r'\bbi\b', 'bilhões'),
    (r'\bmi\b', 'milhões'),
    (r'\btri\b', 'trilhões'),

    # Percentages - ensure TTS reads "por cento"
    (r'(\d)\s*%', r'\1 por cento'),
    (r'(\d),(\d+)\s*pp\b', r'\1 vírgula \2 pontos percentuais'),
    (r'(\d)\s*pp\b', r'\1 pontos percentuais'),

    # Common O&G abbreviations
    (r'\bANP\b', 'A.N.P.'),
    (r'\bANM\b', 'A.N.M.'),
    (r'\bOPEP\+?', 'OPEP'),
    (r'\bFPSO\b', 'F.P.S.O.'),
    (r'\bAIE\b', 'A.I.É.'),
    (r'\bIBP\b', 'I.B.P.'),
    (r'\bIPCA\b', 'I.P.C.A.'),
    (r'\bEBITDA\b', 'EBITDA'),
    (r'\bLRCAP\b', 'Leilão de Reserva de Capacidade'),
    (r'\bPDAC\b', 'P.D.A.C.'),
    (r'\bEPC\b', 'E.P.C.'),
    (r'\bP&I\b', 'P. and I.'),
    (r'\bG7\b', 'G. sete'),
    (r'\bEAU\b', 'Emirados Árabes'),

    # Company tickers
    (r'\bPETR4\b', 'Petrobras preferencial'),
    (r'\bPETR3\b', 'Petrobras ordinária'),
    (r'\bPRIO3\b', 'PRIO'),
    (r'\bBRAV3\b', 'Brava Energia'),
    (r'\bVALE3\b', 'Vale'),

    # Directions / variations
    (r'\ba/a\b', 'ano a ano'),
    (r'\bvs\.\s*', 'versus '),
    (r'\b4T25\b', 'quarto trimestre de 2025'),
    (r'\b3T25\b', 'terceiro trimestre de 2025'),
    (r'\b2T25\b', 'segundo trimestre de 2025'),
    (r'\b1T25\b', 'primeiro trimestre de 2025'),
    (r'\b3T24\b', 'terceiro trimestre de 2024'),
    (r'\b4T24\b', 'quarto trimestre de 2024'),
    (r'\b1T26\b', 'primeiro trimestre de 2026'),
    (r'\b2T26\b', 'segundo trimestre de 2026'),
    (r'\b3T26\b', 'terceiro trimestre de 2026'),
    (r'\b4T26\b', 'quarto trimestre de 2026'),
]


def extract_text_bs4(html_path):
    """Extract readable text using BeautifulSoup — only narrative paragraphs."""
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

    # Remove all source paragraphs (class="source" or starting with "Fontes:")
    for p in container.find_all('p'):
        p_class = p.get('class', [])
        if 'source' in p_class:
            p.decompose()
            continue
        text = p.get_text(strip=True)
        if text.startswith('Fontes:') or text.startswith('Fonte:'):
            p.decompose()

    # Extract text with newlines between paragraphs for natural pacing
    paragraphs = []
    for el in container.find_all(['p', 'h2', 'h3']):
        text = el.get_text(strip=True)
        text = SYMBOLS_RE.sub('', text)
        text = text.strip()
        if len(text) > 10:  # Skip very short fragments
            paragraphs.append(text)

    return '\n\n'.join(paragraphs)


def extract_text_regex(html_path):
    """Fallback text extraction using regex."""
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    html = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<[^>]+>', ' ', html)
    text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    text = text.replace('&#8592;', '').replace('&times;', '')
    text = SYMBOLS_RE.sub('', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_text(html_path):
    """Extract text from HTML edition file."""
    if BeautifulSoup:
        return extract_text_bs4(html_path)
    return extract_text_regex(html_path)


def expand_abbreviations(text):
    """Expand abbreviations and units so TTS reads them naturally."""
    for pattern, replacement in ABBREVIATIONS:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE if pattern[0] != '\\' else 0)
    return text


def clean_text_for_speech(text):
    """Clean and prepare text for natural TTS reading."""
    # Em dash — replace with period for sentence break
    text = text.replace(' — ', '. ')
    text = text.replace('—', '. ')

    # Remove HTML entities
    text = text.replace('&amp;', ' e ')
    text = text.replace('&middot;', '.')
    text = text.replace('&nbsp;', ' ')

    # Remove URLs
    text = re.sub(r'https?://\S+', '', text)

    # Remove email addresses
    text = re.sub(r'\S+@\S+\.\S+', '', text)

    # Remove standalone parenthetical abbreviations like (ANP)
    text = re.sub(r'\(([A-Z]{2,})\)', r'\1', text)

    # Expand abbreviations BEFORE other cleanup
    text = expand_abbreviations(text)

    # Ensure paragraph breaks become sentence breaks
    text = re.sub(r'\n\n+', '. ', text)
    text = re.sub(r'\n', '. ', text)

    # Clean up multiple periods
    text = re.sub(r'\.[\s.]+\.', '. ', text)
    text = re.sub(r'\.{2,}', '.', text)

    # Remove content between [ ] (often references)
    text = re.sub(r'\[[^\]]*\]', '', text)

    # Clean "Fontes:" lines that might have slipped through
    text = re.sub(r'Fontes?:.*?(?=\.|$)', '', text)

    # Clean multiple spaces
    text = re.sub(r'\s+', ' ', text).strip()

    return text


async def generate_audio(text, output_path, voice=VOICE, rate=RATE):
    """Generate MP3 from text using edge-tts (plain text, no SSML)."""
    clean_text = clean_text_for_speech(text)

    intro = 'Você está ouvindo o O and G plus Mining Intelligence Brief. '
    closing = '. Fim da edição. Obrigado por ouvir.'

    full_text = intro + clean_text + closing

    print(f"Generating audio ({len(clean_text)} chars after cleanup)...")
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
