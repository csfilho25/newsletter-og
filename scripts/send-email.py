#!/usr/bin/env python3
"""
The Sector — Email Sender
Sends newsletter edition via Gmail SMTP with App Password.
Requires: GMAIL_APP_PASSWORD environment variable set.
"""

import sys
import os
import re
import csv
import io
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from urllib.request import urlopen
from urllib.error import URLError

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Install beautifulsoup4: pip install beautifulsoup4")
    sys.exit(1)

# Config
GMAIL_USER = "carlos.alberto.dias.souza@gmail.com"
DEFAULT_RECIPIENT = "cs_filho@icloud.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Google Sheets CSV URL (published to web)
SUBSCRIBERS_CSV_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRZHXRXZQqm4CkFTF63VNQrzXA2Hmt--l3mKjxgsbYRVL7k5dRTC-0FngTx62BW21R7wFadHxr6mOpV/pub?output=csv"

# Portuguese month names
MONTHS_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}
MONTHS_SHORT = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Abr", 5: "Mai", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Set", 10: "Out", 11: "Nov", 12: "Dez"
}


def extract_metadata(html_path):
    """Extract edition metadata from HTML file."""
    with open(html_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')

    # Edition number from meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    edition_num = "???"
    if meta_desc:
        m = re.search(r'Ed\.\s*#(\d+)', meta_desc.get('content', ''))
        if m:
            edition_num = m.group(1)

    # Date from filename
    date_str = html_path.stem  # e.g., "2026-03-10"
    parts = date_str.split('-')
    year, month, day = int(parts[0]), int(parts[1]), int(parts[2])
    date_display = f"{day} {MONTHS_SHORT[month]} {year}"
    date_subject = f"{day:02d}/{MONTHS_SHORT[month]}/{year}"

    # Extract executive summary
    exec_summary = soup.find(class_='exec-summary')
    summary_items = []
    if exec_summary:
        for li in exec_summary.find_all('li')[:7]:
            summary_items.append(li.decode_contents())

    # Extract key numbers from market-ticker (new format) or numbers-grid (legacy)
    numbers = []
    ticker = soup.find(class_='market-ticker')
    if ticker:
        for item in ticker.find_all(class_='ticker-item')[:8]:
            symbol = item.find(class_='ticker-symbol')
            price = item.find(class_='ticker-price')
            change = item.find(class_='ticker-change')
            if symbol and price:
                change_text = change.get_text(strip=True) if change else ''
                change_cls = change.get('class', []) if change else []
                numbers.append({
                    'value': price.get_text(strip=True),
                    'label': symbol.get_text(strip=True),
                    'change': change_text,
                    'direction': 'up' if any('up' in c or 'positive' in c for c in change_cls) else
                                 'down' if any('down' in c or 'negative' in c for c in change_cls) else 'neutral'
                })
    else:
        # Legacy format fallback
        numbers_grid = soup.find(class_='numbers-grid')
        if numbers_grid:
            for card in numbers_grid.find_all(class_='num-card')[:8]:
                value = card.find(class_='value')
                label = card.find(class_='label')
                change = card.find(class_='change')
                if value and label:
                    numbers.append({
                        'value': value.get_text(strip=True),
                        'label': label.get_text(strip=True),
                        'change': change.get_text(strip=True) if change else '',
                        'direction': 'up' if change and 'up' in change.get('class', []) else
                                     'down' if change and 'down' in change.get('class', []) else 'neutral'
                    })

    # Extract alert banner
    alert = soup.find(class_='alert-banner')
    alert_text = ""
    if alert:
        alert_el = alert.find(class_='alert-text')
        if alert_el:
            alert_text = alert_el.decode_contents()

    # OG description
    og_desc = soup.find('meta', attrs={'property': 'og:description'})
    og_text = og_desc.get('content', '') if og_desc else ''

    return {
        'edition_num': edition_num,
        'date_display': date_display,
        'date_subject': date_subject,
        'date_iso': date_str,
        'year': year,
        'month': month,
        'day': day,
        'summary_items': summary_items,
        'numbers': numbers,
        'alert_text': alert_text,
        'og_description': og_text,
    }


def build_number_cell(num):
    """Build a key number table cell."""
    color_val = '#296FB1'
    color_change = '#64748b'
    if num['direction'] == 'up':
        color_change = '#16a34a'
    elif num['direction'] == 'down':
        color_val = '#dc2626'
        color_change = '#dc2626'

    return f'''<td style="background:#f8fafc;border-radius:8px;padding:14px 8px;text-align:center;border:1px solid #e2e8f0;width:25%;">
        <div style="font-size:16px;font-weight:700;color:{color_val};">{num['value']}</div>
        <div style="color:#64748b;margin-top:4px;font-size:11px;">{num['label']}</div>
        <div style="color:{color_change};font-size:10px;margin-top:2px;">{num['change']}</div>
    </td>'''


def build_email_html(meta):
    """Build the full email HTML — dark navy + gold identity matching thesector.com.br."""
    edition_url = f"https://thesector.com.br/editions/{meta['date_iso']}.html"
    listen_url = f"{edition_url}#listen"
    subscribe_url = "https://thesector.com.br/#assinar"
    linkedin_url = "https://www.linkedin.com/company/the-sector-news/"

    # Colors matching site identity
    navy = "#0a1628"
    navy_mid = "#0d2137"
    navy_light = "#122d4a"
    gold = "#e8b94a"
    gold_dark = "#c9953c"
    blue = "#296FB1"
    blue_dark = "#1d5a94"

    # Summary list with sector emoji icons
    summary_html = ""
    bullet_icons = ["&#9981;", "&#128230;", "&#128200;", "&#9889;", "&#9935;", "&#127758;", "&#128270;"]
    for i, item in enumerate(meta['summary_items']):
        icon = bullet_icons[i] if i < len(bullet_icons) else "&#9656;"
        bg = "#f8fafc" if i % 2 == 0 else "#ffffff"
        summary_html += f'''<tr>
  <td style="background:{bg};padding:12px 16px;font-size:13px;color:#334155;line-height:1.7;">
    <span style="font-size:16px;margin-right:8px;vertical-align:middle;">{icon}</span>{item}
  </td>
</tr>\n'''

    # Alert section
    alert_section = ""
    if meta['alert_text']:
        alert_section = f'''<tr><td style="padding:0;">
  <table width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="background:#fef2f2;border-left:4px solid #dc2626;padding:16px 28px;">
      <p style="margin:0;font-size:13px;color:#991b1b;line-height:1.6;"><strong style="color:#dc2626;text-transform:uppercase;letter-spacing:0.5px;">&#9888; Alerta Geopolitico:</strong> {meta['alert_text']}</p>
    </td>
  </tr></table>
</td></tr>'''

    # Numbers grid — 4 per row, light cards
    numbers_rows_html = ""
    nums = meta['numbers'][:8]
    for row_start in range(0, len(nums), 4):
        row_nums = nums[row_start:row_start+4]
        cells = ""
        for num in row_nums:
            color_val = navy
            color_change = '#64748b'
            arrow = ''
            if num['direction'] == 'up':
                color_change = '#047857'
                arrow = '&#9650; '
            elif num['direction'] == 'down':
                color_val = '#dc2626'
                color_change = '#dc2626'
                arrow = '&#9660; '
            cells += f'''<td width="25%" style="text-align:center;padding:6px 3px;">
        <div style="background:#f7f9fc;border-radius:8px;padding:12px 4px;border:1px solid #e2e8f0;">
          <div style="font-size:14px;font-weight:700;color:{color_val};">{num['value']}</div>
          <div style="color:{blue};font-size:9px;margin-top:4px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600;">{num['label']}</div>
          <div style="color:{color_change};font-size:10px;margin-top:3px;font-weight:600;">{arrow}{num['change']}</div>
        </div>
      </td>'''
        for _ in range(4 - len(row_nums)):
            cells += '<td width="25%"></td>'
        numbers_rows_html += f'<tr>{cells}</tr>\n'

    # Preheader text
    preheader_items = [item.get_text(strip=True) if hasattr(item, 'get_text') else re.sub(r'<[^>]+>', '', str(item)) for item in meta['summary_items'][:2]]
    preheader = ' | '.join(preheader_items)[:150] if preheader_items else f"The Sector Ed. #{meta['edition_num']}"

    return f'''<!DOCTYPE html>
<html lang="pt-BR" xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="X-UA-Compatible" content="IE=edge">
<title>The Sector Ed. #{meta['edition_num']}</title>
<!--[if mso]><style>table,td,p,a,h1,h2,span {{font-family:Arial,sans-serif !important;}}</style><![endif]-->
</head>
<body style="margin:0;padding:0;background-color:#e2e8f0;font-family:'Helvetica Neue',Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased;">

<!-- Preheader -->
<div style="display:none;font-size:1px;color:#e2e8f0;line-height:1px;max-height:0;max-width:0;opacity:0;overflow:hidden;">{preheader}</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:#e2e8f0;">
<tr><td align="center" style="padding:16px 10px;">

<!-- MAIN CONTAINER -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;border-radius:10px;overflow:hidden;border:1px solid #cbd5e1;">

<!-- GOLD TOP LINE -->
<tr><td style="background:{gold};height:3px;font-size:1px;line-height:1px;">&nbsp;</td></tr>

<!-- HEADER — Dark Navy (like site nav) -->
<tr><td style="background:{navy};padding:32px 28px 28px;text-align:center;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <h1 style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:32px;font-weight:700;letter-spacing:6px;text-transform:uppercase;">
        <span style="color:#ffffff;">THE </span><span style="color:{gold};">SECTOR</span>
      </h1>
    </td></tr>
    <tr><td align="center" style="padding-top:10px;">
      <p style="margin:0;font-size:11px;color:#8ba4c0;letter-spacing:2px;text-transform:uppercase;">Oil &bull; Gas &bull; Energia &bull; Mineracao</p>
    </td></tr>
    <tr><td align="center" style="padding-top:16px;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td style="background:rgba(232,185,74,0.15);border:1px solid rgba(232,185,74,0.3);padding:5px 18px;border-radius:20px;">
          <span style="font-size:12px;color:{gold};font-weight:600;">Ed. #{meta['edition_num']} &middot; {meta['date_display']}</span>
        </td>
      </tr></table>
    </td></tr>
  </table>
</td></tr>

<!-- GOLD DIVIDER LINE -->
<tr><td style="background:{gold_dark};height:2px;font-size:1px;line-height:1px;">&nbsp;</td></tr>

{alert_section}

<!-- ACTION BUTTONS -->
<tr><td style="background:#ffffff;padding:22px 28px 18px;text-align:center;">
  <table role="presentation" cellpadding="0" cellspacing="0" align="center"><tr>
    <td style="padding-right:6px;">
      <a href="{edition_url}" style="display:inline-block;background:{blue};color:#ffffff;padding:11px 22px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700;">&#128214; Ler no Navegador</a>
    </td>
    <td style="padding-left:6px;">
      <a href="{listen_url}" style="display:inline-block;background:#ffffff;color:{blue};padding:10px 22px;border-radius:6px;text-decoration:none;font-size:13px;font-weight:700;border:2px solid {blue};">&#127911; Ouvir Edicao</a>
    </td>
  </tr></table>
</td></tr>

<!-- SECTION: RESUMO EXECUTIVO -->
<tr><td style="background:#ffffff;padding:0 28px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="border-bottom:2px solid {gold};padding-bottom:8px;">
      <h2 style="margin:0;font-size:15px;color:{navy};font-weight:700;letter-spacing:0.3px;">
        <span style="color:{gold};margin-right:6px;">&#9656;</span> Resumo Executivo
      </h2>
    </td></tr>
  </table>
</td></tr>
<tr><td style="background:#ffffff;padding:12px 28px 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
    {summary_html}
  </table>
</td></tr>

<!-- SECTION: COTACOES -->
<tr><td style="background:#ffffff;padding:0 28px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td style="border-bottom:2px solid {gold};padding-bottom:8px;">
      <h2 style="margin:0;font-size:15px;color:{navy};font-weight:700;letter-spacing:0.3px;">
        <span style="color:{gold};margin-right:6px;">&#9656;</span> Cotacoes do Dia
      </h2>
    </td></tr>
  </table>
</td></tr>
<tr><td style="background:#ffffff;padding:12px 24px 20px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="4">
    {numbers_rows_html}
  </table>
</td></tr>

<!-- CTA PRINCIPAL -->
<tr><td style="background:#ffffff;padding:8px 28px 20px;text-align:center;">
  <table role="presentation" cellpadding="0" cellspacing="0" align="center"><tr>
    <td style="background:{blue};border-radius:8px;">
      <a href="{edition_url}" style="display:inline-block;padding:14px 44px;color:#ffffff;text-decoration:none;font-size:15px;font-weight:700;letter-spacing:0.3px;">Ler Edicao Completa &rarr;</a>
    </td>
  </tr></table>
  <p style="margin:12px 0 0;font-size:12px;color:#94a3b8;">Gostou? <a href="{subscribe_url}" style="color:{blue};text-decoration:underline;font-weight:600;">Inscreva-se</a> para receber de seg a sex.</p>
</td></tr>

<!-- FOOTER — Dark Navy (like site footer) -->
<tr><td style="background:{navy};padding:28px 28px 20px;text-align:center;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center">
      <p style="margin:0;font-family:Georgia,'Times New Roman',serif;font-size:18px;font-weight:700;letter-spacing:4px;text-transform:uppercase;">
        <span style="color:#ffffff;">THE </span><span style="color:{gold};">SECTOR</span>
      </p>
      <p style="margin:8px 0 0;font-size:11px;color:#8ba4c0;letter-spacing:0.3px;">Inteligencia diaria para decisores do setor energetico e mineral</p>
      <p style="margin:4px 0 0;font-size:11px;color:#8ba4c0;">Edicao diaria seg-sex</p>
    </td></tr>
    <tr><td align="center" style="padding-top:16px;">
      <a href="https://thesector.com.br/" style="color:{gold};text-decoration:none;font-size:12px;font-weight:600;">Portal</a>
      <span style="color:#334155;margin:0 8px;">&middot;</span>
      <a href="{listen_url}" style="color:{gold};text-decoration:none;font-size:12px;font-weight:600;">Ouvir</a>
      <span style="color:#334155;margin:0 8px;">&middot;</span>
      <a href="{linkedin_url}" style="color:{gold};text-decoration:none;font-size:12px;font-weight:600;">LinkedIn</a>
    </td></tr>
    <tr><td align="center" style="padding-top:14px;">
      <p style="margin:0;font-size:9px;color:#4a6380;line-height:1.5;">Powered by Claude AI &middot; Dados publicos &middot; Nao constitui recomendacao de investimento</p>
    </td></tr>
  </table>
</td></tr>

<!-- GOLD BOTTOM LINE -->
<tr><td style="background:{gold};height:3px;font-size:1px;line-height:1px;">&nbsp;</td></tr>

</table>
<!-- END MAIN CONTAINER -->

</td></tr>
</table>
</body>
</html>'''


def fetch_subscribers():
    """Fetch subscriber emails from Google Sheets CSV."""
    subscribers = set()
    # Always include the default recipient
    subscribers.add(DEFAULT_RECIPIENT)

    try:
        print(f"Fetching subscribers from Google Sheets...")
        response = urlopen(SUBSCRIBERS_CSV_URL, timeout=15)
        data = response.read().decode('utf-8')
        reader = csv.reader(io.StringIO(data))
        header = next(reader, None)  # Skip header row

        # Find email column (usually column B = index 1, "Seu melhor email")
        email_col = 1  # default: second column
        if header:
            for i, col in enumerate(header):
                if 'email' in col.lower() or 'e-mail' in col.lower():
                    email_col = i
                    break

        for row in reader:
            if len(row) > email_col:
                email = row[email_col].strip().lower()
                # Basic email validation
                if email and '@' in email and '.' in email.split('@')[-1]:
                    subscribers.add(email)

        print(f"  Found {len(subscribers)} subscriber(s) (including default)")
    except URLError as e:
        print(f"  WARNING: Could not fetch subscribers: {e}")
        print(f"  Sending only to default: {DEFAULT_RECIPIENT}")
    except Exception as e:
        print(f"  WARNING: Error reading subscriber list: {e}")
        print(f"  Sending only to default: {DEFAULT_RECIPIENT}")

    return list(subscribers)


def send_email(html_path, test_mode=False):
    """Send newsletter email via Gmail SMTP to all subscribers (or just default if test_mode)."""
    app_password = os.environ.get('GMAIL_APP_PASSWORD')
    if not app_password:
        print("ERROR: GMAIL_APP_PASSWORD environment variable not set.")
        print("Set it with: setx GMAIL_APP_PASSWORD \"xxxx xxxx xxxx xxxx\"")
        print("Get your App Password at: https://myaccount.google.com/apppasswords")
        sys.exit(1)

    html_path = Path(html_path)
    if not html_path.exists():
        print(f"File not found: {html_path}")
        sys.exit(1)

    print(f"Reading edition: {html_path.name}")
    meta = extract_metadata(html_path)

    subject = f"The Sector Ed. #{meta['edition_num']} — {meta['date_subject']}"
    if test_mode:
        subject = f"[TESTE] {subject}"
    email_html = build_email_html(meta)

    # Plain text fallback
    plain_text = f"The Sector - Ed. #{meta['edition_num']}\n"
    plain_text += f"Data: {meta['date_display']}\n\n"
    plain_text += f"Leia no navegador: https://thesector.com.br/editions/{meta['date_iso']}.html\n"

    # Get recipients
    if test_mode:
        recipients = [DEFAULT_RECIPIENT]
        print(f"TEST MODE: sending only to {DEFAULT_RECIPIENT}")
    else:
        recipients = fetch_subscribers()

    print(f"Subject: {subject}")
    print(f"Sending to {len(recipients)} recipient(s)...")

    # Send individually (BCC-style, each gets their own copy)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, app_password)

            sent = 0
            failed = 0
            for recipient in recipients:
                try:
                    msg = MIMEMultipart('alternative')
                    msg['Subject'] = Header(subject, 'utf-8')
                    msg['From'] = "The Sector <contato@thesector.com.br>"
                    msg['Reply-To'] = 'contato@thesector.com.br'
                    msg['To'] = recipient

                    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
                    msg.attach(MIMEText(email_html, 'html', 'utf-8'))

                    server.send_message(msg)
                    sent += 1
                    print(f"  OK {recipient}")
                except Exception as e:
                    failed += 1
                    print(f"  FAIL {recipient}: {e}")

        print(f"\nDone! Sent: {sent}, Failed: {failed}")
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Authentication failed. Check your GMAIL_APP_PASSWORD.")
        print("Get a new App Password at: https://myaccount.google.com/apppasswords")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR connecting to SMTP: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python send-email.py <edition.html> [--test]")
        print("Example: python send-email.py editions/2026-03-10.html")
        print("         python send-email.py editions/2026-03-10.html --test  (only sends to default recipient)")
        sys.exit(1)

    test_mode = '--test' in sys.argv
    send_email(sys.argv[1], test_mode=test_mode)


if __name__ == '__main__':
    main()
