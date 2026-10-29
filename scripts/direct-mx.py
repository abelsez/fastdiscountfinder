#!/usr/bin/env python3
"""direct-mx.py — deliver straight to the recipient's MX, no ESP, no credentials.

Why it exists: outbound port 25 is open from this line (verified against
gmail-smtp-in.l.google.com and mx01.mail.icloud.com), so mail *can* be handed
over without Brevo's 300/day cap. It will almost certainly fail authentication
(no SPF entry for this IP, no DKIM key for the domain), which is why this is a
diagnostic + last-resort tool, not the default path.

usage:
  direct-mx.py --to jmaclive101@gmail.com --from abel@smartworld.press \
               --subject "..." --html email/x.html --txt email/x.txt [--dry-run]
Prints the full SMTP dialogue so accept/reject is visible, not guessed.
"""
from __future__ import annotations

import argparse
import json
import smtplib
import socket
import ssl
import sys
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path


def mx_for(domain: str) -> list[str]:
    for url in (f"https://cloudflare-dns.com/dns-query?name={domain}&type=MX",
                f"https://dns.google/resolve?name={domain}&type=MX"):
        try:
            req = urllib.request.Request(url, headers={"accept": "application/dns-json"})
            with urllib.request.urlopen(req, timeout=20) as r:
                d = json.loads(r.read().decode())
            hosts = sorted(((int(a["data"].split()[0]), a["data"].split()[-1].rstrip("."))
                            for a in d.get("Answer", []) if a.get("type") == 15))
            if hosts:
                return [h for _, h in hosts]
        except Exception:  # noqa: BLE001
            continue
    return []


def build(from_addr: str, to: str, subject: str, html: str, text: str) -> EmailMessage:
    m = EmailMessage()
    m["Subject"] = subject
    m["From"] = from_addr
    m["To"] = to
    m["Date"] = formatdate(localtime=True)
    m["Message-ID"] = make_msgid(domain=from_addr.split("@")[-1])
    m["Reply-To"] = "jmaclive101@gmail.com"
    m["List-Unsubscribe"] = f"<mailto:unsubscribe@{from_addr.split('@')[-1]}>"
    m["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    m.set_content(text or "HTML mail")
    if html:
        m.add_alternative(html, subtype="html")
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True)
    ap.add_argument("--from", dest="sender", required=True)
    ap.add_argument("--subject", required=True)
    ap.add_argument("--html")
    ap.add_argument("--txt")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    domain = a.to.split("@")[-1]
    hosts = mx_for(domain)
    print(f"recipient {a.to} -> MX: {hosts or 'NONE'}")
    if not hosts:
        return 2
    html = Path(a.html).read_text() if a.html else ""
    text = Path(a.txt).read_text() if a.txt else ""
    msg = build(a.sender, a.to, a.subject, html, text)
    print(f"from {a.sender} | {len(msg.as_bytes())} bytes | pretending SMTP as {socket.gethostname()}")

    if a.dry_run:
        print("dry-run: message built, nothing dialled")
        return 0

    for host in hosts[:3]:
        print(f"\n-- {host}:25")
        try:
            s = smtplib.SMTP(host, 25, timeout=25)
            s.set_debuglevel(0)
            code, resp = s.ehlo(socket.gethostname())
            print(f"   EHLO -> {code} {resp.decode(errors='replace')[:80]}")
            code, resp = s.mail(a.sender)
            print(f"   MAIL FROM -> {code} {resp.decode(errors='replace')[:110]}")
            if code >= 400:
                s.quit(); continue
            code, resp = s.rcpt(a.to)
            print(f"   RCPT TO   -> {code} {resp.decode(errors='replace')[:110]}")
            if code >= 400:
                s.quit(); continue
            code, resp = s.data(msg.as_bytes())
            print(f"   DATA      -> {code} {resp.decode(errors='replace')[:140]}")
            s.quit()
            if 200 <= code < 300:
                print("   RESULT: accepted by the receiving MX (placement is a separate question)")
                return 0
        except Exception as e:  # noqa: BLE001
            print(f"   error: {type(e).__name__}: {e}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
