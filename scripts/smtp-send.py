#!/usr/bin/env python3
"""Send the campaign through Brevo's SMTP relay (smtp-relay.brevo.com).

Why this exists: the Brevo *API* is IP-allowlisted on this account (401
"unrecognised IP address"), but SMTP-key IP blocking is OFF by default — so an
SMTP key sends fine from here without touching the allowlist.

usage:
  smtp-send.py --subject "..." --html email/at.html --txt email/at.txt \
               --to a@x.com --to b@y.com [--dry-run]
  smtp-send.py ... --seed                # sends to BREVO_SEED_ADDRESSES only

creds: ~/.secrets/brevo-smtp.env
  BREVO_SMTP_KEY=xsmtpsib-...
  BREVO_SMTP_USER=<account email used to log in at brevo.com>
  BREVO_SENDER_EMAIL=you@yourdomain.com
  BREVO_SENDER_NAME="Fast Discount Finder"
  BREVO_SEED_ADDRESSES="gmail@...,outlook@..."
"""
from __future__ import annotations

import argparse
import smtplib
import ssl
import sys
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from pathlib import Path

ENVF = Path.home() / ".secrets" / "brevo-smtp.env"
HOST = "smtp-relay.brevo.com"


def load_env(path: Path = ENVF) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"')
    return out


def build(env: dict[str, str], subject: str, html: str, text: str, to: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f'{env.get("BREVO_SENDER_NAME", "Fast Discount Finder")} <{env["BREVO_SENDER_EMAIL"]}>'
    msg["To"] = to
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain=env["BREVO_SENDER_EMAIL"].split("@")[-1])
    if env.get("BREVO_REPLY_TO"):
        msg["Reply-To"] = env["BREVO_REPLY_TO"]
    msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{env['BREVO_SENDER_EMAIL'].split('@')[-1]}>, <https://{env['BREVO_SENDER_EMAIL'].split('@')[-1]}/unsubscribe>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.set_content(text or "This message requires an HTML-capable client.")
    msg.add_alternative(html, subtype="html")
    return msg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--subject", required=True)
    ap.add_argument("--html", required=True)
    ap.add_argument("--txt")
    ap.add_argument("--to", action="append", default=[])
    ap.add_argument("--seed", action="store_true", help="send only to BREVO_SEED_ADDRESSES")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--port", type=int, default=587)
    args = ap.parse_args()

    env = load_env()
    missing = [k for k in ("BREVO_SMTP_KEY", "BREVO_SMTP_USER", "BREVO_SENDER_EMAIL") if not env.get(k)]
    html = Path(args.html).read_text(encoding="utf-8")
    text = Path(args.txt).read_text(encoding="utf-8") if args.txt and Path(args.txt).exists() else ""

    recipients = list(args.to)
    if args.seed:
        recipients = [r.strip() for r in env.get("BREVO_SEED_ADDRESSES", "").split(",") if r.strip()]
    recipients = list(dict.fromkeys(recipients))

    print(f"relay      : {HOST}:{args.port} (STARTTLS)")
    print(f"from       : {env.get('BREVO_SENDER_NAME','?')} <{env.get('BREVO_SENDER_EMAIL','MISSING')}>")
    print(f"login      : {env.get('BREVO_SMTP_USER','MISSING')}")
    print(f"key        : {'set(len=%d)' % len(env['BREVO_SMTP_KEY']) if env.get('BREVO_SMTP_KEY') else 'MISSING'}")
    print(f"subject    : {args.subject}")
    print(f"html/txt   : {len(html)} B / {len(text)} B")
    print(f"recipients : {len(recipients)} {recipients[:5]}{' …' if len(recipients) > 5 else ''}")

    if missing:
        print(f"ERROR: missing {', '.join(missing)} in {ENVF}", file=sys.stderr)
        return 2
    if not recipients:
        print("ERROR: no recipients (--to or --seed)", file=sys.stderr)
        return 2
    if args.dry_run:
        msg = build(env, args.subject, html, text, recipients[0])
        print("dry-run    : message built, headers:")
        for h in ("Subject", "From", "List-Unsubscribe", "List-Unsubscribe-Post"):
            print(f"   {h}: {msg[h]}")
        print("             not sent")
        return 0
    if env.get("BREVO_ALLOW_SEND") != "yes":
        print("refusing to send: set BREVO_ALLOW_SEND=yes in ~/.secrets/brevo-smtp.env", file=sys.stderr)
        return 3

    ctx = ssl.create_default_context()
    sent = failed = 0
    try:
        with smtplib.SMTP(HOST, args.port, timeout=45) as s:
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
            s.login(env["BREVO_SMTP_USER"], env["BREVO_SMTP_KEY"])
            for rcpt in recipients:
                try:
                    s.send_message(build(env, args.subject, html, text, rcpt))
                    sent += 1
                    print(f"  ok   {rcpt}")
                except smtplib.SMTPException as exc:
                    failed += 1
                    print(f"  FAIL {rcpt}: {exc}")
    except smtplib.SMTPAuthenticationError as exc:
        print(f"AUTH FAILED: {exc.smtp_code} {exc.smtp_error.decode(errors='replace')[:200]}", file=sys.stderr)
        print("  -> generate an SMTP key: Brevo > Settings > SMTP & API > SMTP tab > Generate a new SMTP key", file=sys.stderr)
        return 4
    except Exception as exc:  # noqa: BLE001
        print(f"connection error: {exc}", file=sys.stderr)
        return 5
    print(f"done: {sent} sent, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
