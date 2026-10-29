# Sender options — what is actually reachable from this device

Verified 2026-10-29 by handshake, not by reading pricing pages.

## Tested now

| path | result | evidence |
|---|---|---|
| **Brevo API** (`api.brevo.com`) | works — 300 sends/day account cap, 0 credits left today | `#130` sent 292/delivered 285 |
| **Brevo SMTP relay** `smtp-relay.brevo.com:587` | reachable, needs an `xsmtpsib-` SMTP key (API keys give 535) | SMTP AUTH probe |
| **Direct-to-MX, port 25** | port open to `gmail-smtp-in.l.google.com` + `mx01.mail.icloud.com`; **Gmail rejects the DATA phase** | `550 5.7.1 [102.213.179.7] The IP you're using to send mail is not authorized to send email directly to our servers. Please use the SMTP relay at your service provider instead.` |
| Yahoo MX :25 | TCP timeout | — |
| Gmail/Workspace SMTP | needs app password (no credential on device) | — |

So "no-account workarounds" are exhausted: the receiving side refuses unknown sending IPs
before it ever looks at our content. `scripts/direct-mx.py` keeps this reproducible.

## What would add capacity (per account, not per IP)

| provider | free limit | domain DNS required? | single verified sender enough? | verdict |
|---|---|---|---|---|
| Brevo | 300/day (~9k/mo) | no (branding footer on free) | yes | in use |
| **Mailjet** | 6,000/mo, **200/day**, max 1,000 contacts | no | **yes** | best next add: +200/day, no DNS |
| Resend | 3,000/mo, 100/day | **yes** (SPF+DKIM) | no | blocked on DNS |
| MailerSend | 500/mo, 100/day | **yes** + card on file | no | blocked on DNS + card |
| SendGrid | 60-day trial, 100/day | optional | yes | temporary only |
| Amazon SES | 62k/mo from EC2; sandbox 200/day but **every recipient must be verified** | yes for production | no | useless for a cold list |
| Postmark | 100/mo | optional (sender signature) | yes | too small for 1,330 |
| Selzy | ~1,000 trial | optional | yes | one-shot only |
| Loops | 4,000 per 30 days | **yes** | no | blocked on DNS |
| Zoho ZeptoMail | paid credits | yes | no | no free tier |

Capacity math for the 1,330-contact base: **Brevo alone = 5 days**. Brevo + Mailjet =
**3 days**. Add Resend/MailerSend only after `smartworld.press` gets `include:spf.brevo.com`
and their DKIM records (already aligned for Brevo, not for the others).

## Armed automation

```
termux-job-scheduler --pending      # Job 1: ~/bin/drip-run, every 6h, persisted
~/fastdiscountfinder/scripts/drip-send.py --status
~/fastdiscountfinder/scripts/multi-send.py --status
```
`drip-send.py` sends one credit-limited batch per run, records every address in
`state/drip.json`, skips blacklisted contacts, stops if Brevo suspends a campaign, and keeps
10 credits in reserve. `multi-send.py` spreads the same campaign across every key present in
`~/.secrets/senders.env` (Brevo, Mailjet, Resend, MailerSend, generic SMTP) with per-provider
daily caps and its own ledger.
