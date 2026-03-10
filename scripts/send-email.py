#!/usr/bin/env python3
"""
O&G + Mining Intelligence Brief — Email Sender
Sends newsletter edition via Gmail SMTP with App Password.
Requires: GMAIL_APP_PASSWORD environment variable set.
"""

import sys
import os
import re
import smtplib
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Install beautifulsoup4: pip install beautifulsoup4")
    sys.exit(1)

# Config
GMAIL_USER = "carlos.alberto.dias.souza@gmail.com"
RECIPIENT = "cs_filho@icloud.com"
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

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

    # Extract key numbers
    numbers = []
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
    """Build the full email HTML with inline styles."""
    edition_url = f"https://csfilho25.github.io/newsletter-og/editions/{meta['date_iso']}.html"
    listen_url = f"{edition_url}#listen"

    # Summary list
    summary_html = ""
    for item in meta['summary_items']:
        summary_html += f'<li style="padding:4px 0;">{item}</li>\n'

    # Alert section
    alert_section = ""
    if meta['alert_text']:
        alert_section = f'''<tr><td style="padding:0 24px;">
  <div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:8px;padding:16px 18px;margin-top:24px;">
    <p style="margin:0;font-size:13px;color:#991b1b;line-height:1.6;">{meta['alert_text']}</p>
  </div>
</td></tr>'''

    # Numbers grid (2 rows of 4)
    numbers_row1 = ""
    numbers_row2 = ""
    for i, num in enumerate(meta['numbers'][:8]):
        cell = build_number_cell(num)
        if i < 4:
            numbers_row1 += cell
        else:
            numbers_row2 += cell

    numbers_section = f'''<tr>{numbers_row1}</tr>'''
    if numbers_row2:
        numbers_section += f'\n<tr><td colspan="4" style="height:8px;"></td></tr>\n<tr>{numbers_row2}</tr>'

    return f'''<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:'Helvetica Neue',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 0;">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

<!-- HEADER -->
<tr><td style="background:linear-gradient(135deg,#1a4a73 0%,#296FB1 50%,#3b82c4 100%);padding:36px 32px;text-align:center;">
  <div style="font-size:28px;margin-bottom:8px;">&#9981;&#9935;&#9889;</div>
  <h1 style="margin:0;font-size:22px;color:#ffffff;font-weight:700;">O&amp;G + Mining Intelligence Brief</h1>
  <p style="margin:6px 0 0;font-size:13px;color:rgba(255,255,255,0.8);">Oil, Gas, Energia &amp; Mineracao — Edicao Completa</p>
  <div style="margin-top:16px;display:inline-block;">
    <span style="display:inline-block;background:rgba(255,255,255,0.15);color:#fff;padding:5px 14px;border-radius:20px;font-size:12px;font-weight:600;">Ed. #{meta['edition_num']} &middot; {meta['date_display']}</span>
  </div>
</td></tr>

{alert_section}

<!-- ACTIONS -->
<tr><td style="padding:20px 24px;text-align:center;">
  <a href="{edition_url}" style="display:inline-block;background:#296FB1;color:#ffffff;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;margin-right:10px;">&#128214; Ler no Navegador</a>
  <a href="{listen_url}" style="display:inline-block;background:#ecfdf5;color:#047857;padding:12px 28px;border-radius:8px;text-decoration:none;font-size:14px;font-weight:700;border:1px solid #a7f3d0;">&#127911; Ouvir Edicao</a>
</td></tr>

<!-- RESUMO -->
<tr><td style="padding:0 24px;">
  <h2 style="font-size:16px;color:#1e293b;margin:0 0 14px;border-bottom:2px solid #296FB1;padding-bottom:8px;">&#128203; Resumo Executivo</h2>
  <ul style="margin:0;padding:0 0 0 18px;font-size:13px;color:#334155;line-height:1.8;">
    {summary_html}
  </ul>
</td></tr>

<!-- KEY NUMBERS -->
<tr><td style="padding:24px;">
  <h2 style="font-size:16px;color:#1e293b;margin:0 0 14px;border-bottom:2px solid #296FB1;padding-bottom:8px;">&#128202; Key Numbers</h2>
  <table width="100%" cellpadding="0" cellspacing="8" style="font-size:12px;">
    {numbers_section}
  </table>
</td></tr>

<!-- CTA -->
<tr><td style="padding:0 24px 24px;text-align:center;">
  <a href="{edition_url}" style="display:inline-block;background:#296FB1;color:#ffffff;padding:14px 40px;border-radius:8px;text-decoration:none;font-size:15px;font-weight:700;">Ler Edicao Completa &#8594;</a>
</td></tr>

<!-- FOOTER -->
<tr><td style="background:#f8fafc;padding:24px 32px;border-top:1px solid #e2e8f0;text-align:center;">
  <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.6;">
    O&amp;G + Mining Intelligence Brief<br>
    Inteligencia diaria para decisores do setor energetico e mineral<br>
    <a href="https://csfilho25.github.io/newsletter-og/" style="color:#296FB1;text-decoration:none;">Portal</a> &middot;
    <a href="{listen_url}" style="color:#296FB1;text-decoration:none;">Ouvir</a>
  </p>
  <p style="margin:8px 0 0;font-size:10px;color:#cbd5e1;">Powered by Claude AI &middot; Dados publicos &middot; Nao constitui recomendacao de investimento</p>
</td></tr>

</table>
</td></tr>
</table>
</body>
</html>'''


def send_email(html_path):
    """Send newsletter email via Gmail SMTP."""
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

    subject = f"O&G Brief Ed. #{meta['edition_num']} — {meta['date_subject']}"
    email_html = build_email_html(meta)

    # Build message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = GMAIL_USER
    msg['To'] = RECIPIENT

    # Plain text fallback
    plain_text = f"O&G + Mining Intelligence Brief - Ed. #{meta['edition_num']}\n"
    plain_text += f"Data: {meta['date_display']}\n\n"
    plain_text += f"Leia no navegador: https://csfilho25.github.io/newsletter-og/editions/{meta['date_iso']}.html\n"

    msg.attach(MIMEText(plain_text, 'plain', 'utf-8'))
    msg.attach(MIMEText(email_html, 'html', 'utf-8'))

    # Send
    print(f"Sending to: {RECIPIENT}")
    print(f"Subject: {subject}")

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(GMAIL_USER, app_password)
            server.send_message(msg)
        print("Email sent successfully!")
    except smtplib.SMTPAuthenticationError:
        print("ERROR: Authentication failed. Check your GMAIL_APP_PASSWORD.")
        print("Get a new App Password at: https://myaccount.google.com/apppasswords")
        sys.exit(1)
    except Exception as e:
        print(f"ERROR sending email: {e}")
        sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python send-email.py <edition.html>")
        print("Example: python send-email.py editions/2026-03-10.html")
        sys.exit(1)

    send_email(sys.argv[1])


if __name__ == '__main__':
    main()
