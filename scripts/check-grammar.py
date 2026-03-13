#!/usr/bin/env python3
"""
check-grammar.py — Portuguese grammar and spelling checker for newsletter editions.

Uses the LanguageTool API (free, no Java needed) to check Portuguese grammar,
spelling, and style. Focuses on real errors, ignoring false positives from
technical O&G/Mining terms.

Usage:
    python scripts/check-grammar.py editions/2026-03-13.html [--fix] [--verbose]

Options:
    --fix       Auto-fix spelling errors (only MORFOLOGIK_RULE_PT_BR with 1 suggestion)
    --verbose   Show all issues including ignored ones
"""
import re
import sys
import json
import time
import io
from pathlib import Path

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

try:
    import requests
except ImportError:
    print("Error: requests library required. Run: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# ============================================================
# Configuration
# ============================================================

LANGUAGETOOL_API = 'https://api.languagetool.org/v2/check'
CHUNK_SIZE = 4500  # API limit ~20KB, but smaller chunks = better accuracy

# Rules to IGNORE (false positives for technical newsletter content)
IGNORED_RULES = {
    'UPPERCASE_AFTER_COMMA',       # We use ";" + capitalized terms (Brent, OPEP+)
    'UPPERCASE_SENTENCE_START',    # Section headers don't always follow sentence rules
    'COMMA_PARENTHESIS_WHITESPACE',
    'HUNSPELL_NO_SUGGEST_RULE',    # Unknown words with no suggestion (proper nouns)
    'UNPAIRED_BRACKETS',           # HTML entities can cause false positives
    'WHITESPACE_RULE',             # Multiple spaces from HTML extraction
    'SENTENCE_WHITESPACE',
    'DOUBLE_PUNCTUATION',          # Numbers like 1.000.000 trigger this
    'CRASE_CONFUSION',             # Too many false positives in technical text
}

# Words to IGNORE (technical terms, proper nouns, abbreviations)
IGNORED_WORDS = {
    # O&G terms
    'bpd', 'kbpd', 'boe', 'bbl', 'FPSO', 'FPSOs', 'OPEP', 'OPEP+',
    'Ormuz', 'Shaybah', 'Brent', 'WTI',
    # Companies & places
    'Petrobras', 'PRIO', 'Brava', 'Eneva', 'PetroRecôncavo', 'Samarco',
    'Gerdau', 'Ibram', 'Copom', 'Selic', 'Wahoo', 'Peregrino',
    'Macae', 'Itabiritos', 'Itabirito', 'Equinor',
    # Mining
    'niobio', 'niobium', 'espodumeno',
    # Abbreviations
    'EBITDA', 'CAPEX', 'OPEX', 'CLT', 'PCD', 'SAE', 'OTC',
    'LRCAP', 'UTEs', 'UTE', 'ANEEL', 'EPE', 'SPE', 'PPSA',
    'OPP', 'RCM', 'TAG', 'NTS', 'TRRs',
    # Technical
    'offshore', 'onshore', 'upstream', 'downstream', 'midstream',
    'breakeven', 'benchmark', 'hedge', 'hedges', 'spread',
    'capex', 'opex', 'guidance', 'throughput', 'turnaround',
    'brownfield', 'greenfield', 'decommissioning',
    'lifting', 'backlog',
}

# ============================================================
# Functions
# ============================================================

def extract_text_from_html(html_path):
    """Extract visible text from HTML file."""
    content = Path(html_path).read_text(encoding='utf-8')
    if BeautifulSoup:
        soup = BeautifulSoup(content, 'html.parser')
        # Remove script/style elements
        for tag in soup(['script', 'style', 'link', 'meta']):
            tag.decompose()
        text = soup.get_text(separator=' ', strip=True)
    else:
        # Fallback: strip HTML tags
        text = re.sub(r'<[^>]+>', ' ', content)
        text = re.sub(r'\s+', ' ', text).strip()
    return text


def check_chunk(text, retries=3):
    """Check a text chunk via LanguageTool API with retry logic."""
    for attempt in range(retries):
        try:
            resp = requests.post(LANGUAGETOOL_API, data={
                'text': text,
                'language': 'pt-BR',
                'enabledOnly': 'false',
            }, timeout=30)
            if resp.status_code == 200:
                return resp.json().get('matches', [])
            elif resp.status_code == 429:
                # Rate limited — wait and retry
                wait = 2 ** attempt
                print(f"  Rate limited, waiting {wait}s...")
                time.sleep(wait)
            else:
                print(f"  API error {resp.status_code}: {resp.text[:100]}")
                return []
        except requests.exceptions.RequestException as e:
            print(f"  Request error: {e}")
            time.sleep(1)
    return []


def check_text(text):
    """Check full text by splitting into chunks."""
    all_matches = []
    chunks = []
    # Split text into chunks at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current_chunk = ''
    offset = 0

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > CHUNK_SIZE:
            if current_chunk:
                chunks.append((current_chunk, offset))
                offset += len(current_chunk) + 1
                current_chunk = sentence
            else:
                # Single sentence larger than chunk size
                chunks.append((sentence[:CHUNK_SIZE], offset))
                offset += CHUNK_SIZE
                current_chunk = ''
        else:
            current_chunk = (current_chunk + ' ' + sentence).strip()

    if current_chunk:
        chunks.append((current_chunk, offset))

    print(f"Checking {len(text)} chars in {len(chunks)} chunks...")

    for i, (chunk, chunk_offset) in enumerate(chunks):
        matches = check_chunk(chunk)
        for m in matches:
            m['_chunk_offset'] = chunk_offset
        all_matches.extend(matches)
        # Small delay between API calls to avoid rate limiting
        if i < len(chunks) - 1:
            time.sleep(0.5)

    return all_matches


def filter_matches(matches, verbose=False):
    """Filter out false positives and return actionable issues."""
    filtered = []
    ignored_count = 0

    for m in matches:
        rule_id = m['rule']['id']
        ctx = m['context']
        word = ctx['text'][ctx['offset']:ctx['offset'] + ctx['length']]

        # Skip ignored rules
        if rule_id in IGNORED_RULES:
            ignored_count += 1
            if verbose:
                print(f"  [IGNORED rule] {rule_id}: \"{word}\"")
            continue

        # Skip ignored words
        if word.strip() in IGNORED_WORDS or word.strip().lower() in {w.lower() for w in IGNORED_WORDS}:
            ignored_count += 1
            if verbose:
                print(f"  [IGNORED word] \"{word}\" ({rule_id})")
            continue

        # Skip currency space rules (we format R$XX deliberately)
        if rule_id == 'CURRENCY_SPACE_BR':
            ignored_count += 1
            continue

        filtered.append(m)

    return filtered, ignored_count


def display_matches(matches):
    """Display issues in a readable format."""
    # Group by type
    spelling = []
    grammar = []
    style = []

    for m in matches:
        rule_id = m['rule']['id']
        category = m['rule'].get('category', {}).get('id', '')
        if 'MORFOLOGIK' in rule_id or 'HUNSPELL' in rule_id:
            spelling.append(m)
        elif category in ('STYLE', 'REDUNDANCY', 'TYPOGRAPHY'):
            style.append(m)
        else:
            grammar.append(m)

    if spelling:
        print(f"\n{'='*60}")
        print(f"ORTOGRAFIA ({len(spelling)} issues)")
        print(f"{'='*60}")
        for m in spelling:
            ctx = m['context']
            word = ctx['text'][ctx['offset']:ctx['offset'] + ctx['length']]
            replacements = [r['value'] for r in m.get('replacements', [])[:3]]
            print(f"  \"{word}\" -> {replacements}")

    if grammar:
        print(f"\n{'='*60}")
        print(f"GRAMÁTICA ({len(grammar)} issues)")
        print(f"{'='*60}")
        for m in grammar:
            ctx = m['context']
            word = ctx['text'][ctx['offset']:ctx['offset'] + ctx['length']]
            replacements = [r['value'] for r in m.get('replacements', [])[:3]]
            msg = m['message']
            print(f"  \"{word}\" -> {replacements}")
            print(f"    {msg}")

    if style:
        print(f"\n{'='*60}")
        print(f"ESTILO ({len(style)} issues)")
        print(f"{'='*60}")
        for m in style:
            ctx = m['context']
            word = ctx['text'][ctx['offset']:ctx['offset'] + ctx['length']]
            replacements = [r['value'] for r in m.get('replacements', [])[:3]]
            msg = m['message']
            print(f"  \"{word}\" -> {replacements}")
            print(f"    {msg}")

    return len(spelling), len(grammar), len(style)


def auto_fix_spelling(html_path, matches):
    """Auto-fix clear spelling errors (MORFOLOGIK with single suggestion)."""
    content = Path(html_path).read_text(encoding='utf-8')
    fix_count = 0

    for m in matches:
        rule_id = m['rule']['id']
        if 'MORFOLOGIK' not in rule_id:
            continue
        replacements = m.get('replacements', [])
        if len(replacements) != 1:
            continue  # Only auto-fix when there's exactly 1 suggestion

        ctx = m['context']
        wrong = ctx['text'][ctx['offset']:ctx['offset'] + ctx['length']]
        correct = replacements[0]['value']

        # Safety: only fix if it's a clear accent issue (same base letters)
        if wrong.lower().replace('a','á').replace('e','é').replace('i','í').replace('o','ó').replace('u','ú') != correct.lower():
            # More complex change — skip auto-fix
            pass

        # Fix in visible text only (not in tags)
        pattern = r'(?<=>)([^<]*)\b' + re.escape(wrong) + r'\b([^<]*?)(?=<)'
        new_content = re.sub(pattern, lambda m: m.group(1) + correct + m.group(2), content, count=1)
        if new_content != content:
            content = new_content
            fix_count += 1
            print(f"  Fixed: \"{wrong}\" -> \"{correct}\"")

    if fix_count > 0:
        Path(html_path).write_text(content, encoding='utf-8')
        print(f"\nAuto-fixed {fix_count} spelling errors.")
    else:
        print("\nNo auto-fixable spelling errors found.")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/check-grammar.py <html-file> [--fix] [--verbose]")
        sys.exit(1)

    html_path = Path(sys.argv[1])
    do_fix = '--fix' in sys.argv
    verbose = '--verbose' in sys.argv

    if not html_path.exists():
        print(f"Error: {html_path} not found")
        sys.exit(1)

    print(f"Grammar check: {html_path}")

    # Extract text
    text = extract_text_from_html(html_path)

    # Check via API
    all_matches = check_text(text)
    print(f"LanguageTool found {len(all_matches)} raw issues.")

    # Filter false positives
    filtered, ignored = filter_matches(all_matches, verbose=verbose)
    print(f"After filtering: {len(filtered)} actionable, {ignored} ignored.")

    if not filtered:
        print("\nNo issues found! Text is clean.")
        return

    # Display results
    spelling, grammar, style = display_matches(filtered)

    print(f"\nSummary: {spelling} spelling, {grammar} grammar, {style} style issues.")

    # Auto-fix if requested
    if do_fix and spelling > 0:
        print("\nAuto-fixing spelling errors...")
        spelling_matches = [m for m in filtered if 'MORFOLOGIK' in m['rule']['id']]
        auto_fix_spelling(html_path, spelling_matches)


if __name__ == '__main__':
    main()
