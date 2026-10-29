# Inbox placement — what decides it, and what is still missing

Run the audit any time:

```bash
cd ~/fastdiscountfinder
./scripts/inbox-preflight.sh fastdiscountfinder.com \
  email/edu-custom-2026-10-29.html \
  "Your custom .edu email + 200+ student discounts"
# exit code = number of blockers
```

## Current verdict (2026-10-29)

```
dns auth fails : 1   -> no DKIM on fastdiscountfinder.com
content fails  : 1   -> [[POSTAL-ADDRESS]] placeholder still in the footer
content warnings: 0
```

Everything content-side is clean: 11,997 B (far under Gmail's 102 KB clip), **zero images**,
plain-text alternative shipped, 4 links across 2 domains (both ours/messaging), no
spam-lexicon hits, 0.6% caps ratio, 0 exclamation marks, 47-char subject, controlled preheader.

## Why "no DKIM" is the blocker

| record | value now | effect |
|---|---|---|
| SPF | `v=spf1 a mx include:spf.selzy.com include:spf.efwd.registrar-servers.com include:_spf.mlsend.com ~all` | passes for Selzy / Namecheap forwarding / MailerSend — **not for Brevo** |
| DKIM | none on any selector (`brevo1/2`, `mail`, `mta`, `s1`, `k1`, `google`, …) | Gmail/Outlook cannot verify the signer -> bulk mail goes to spam or is rejected |
| DMARC | `v=DMARC1; p=none;` | monitoring only; fine during warmup |
| MX | Namecheap `eforward*` | domain receives mail; DNS is managed at **Namecheap** |

Sending from this domain through Brevo today = SPF fail (Brevo IPs not listed) + no DKIM
signature = `dmarc=fail` -> spam folder, and Brevo itself may refuse the sender because the
domain is not authenticated in the account.

## Fix A — authenticate the domain (best inbox rate)

Add at Namecheap → Domain List → fastdiscountfinder.com → Advanced DNS. **Edit the existing
SPF TXT, do not create a second one** (two SPF records = automatic permerror):

| type | host | value |
|---|---|---|
| TXT | `@` | `v=spf1 a mx include:spf.selzy.com include:spf.efwd.registrar-servers.com include:_spf.mlsend.com include:spf.brevo.com ~all` |
| CNAME | `brevo1._domainkey` | `b1.fastdiscountfinder-com.dkim.brevo.com` |
| CNAME | `brevo2._domainkey` | `b2.fastdiscountfinder-com.dkim.brevo.com` |
| TXT | `_dmarc` | `v=DMARC1; p=none; rua=mailto:dmarc@fastdiscountfinder.com` (p=none now, `p=quarantine` after ~2 weeks of clean sends) |

> Brevo's dashboard shows the exact DKIM targets for *your* account
> (Settings → Senders, Domains & IPs → Domains). Use those values if they differ from the
> generic `b1/b2.<domain-with-dashes>.dkim.brevo.com` form. Verify after ~10 min with:
> `./scripts/email-auth.sh fastdiscountfinder.com` → must print `DKIM  : brevo1._domainkey -> …`.
> Proton/Cloudflare users: keep these CNAMEs **DNS only** (grey cloud), never proxied.

Then warm: 20–50 recipients/day for 3 days from the transactional stream before the full list.

## Fix B — zero-DNS fallback ("whatever else")

| path | auth | DNS work | From address | limit | trade-off |
|---|---|---|---|---|---|
| **Gmail SMTP** (app password) | Google DKIM/SPF, fully aligned | none | `you@gmail.com` | ~500/day, 100/msg | inbox-friendly, but a gmail From lowers trust for a paid product |
| **MailerSend** | `_spf.mlsend.com` already in your SPF | DKIM CNAMEs only | `@fastdiscountfinder.com` | free tier | Brevo's direct competitor, same API shape |
| **Selzy** | `spf.selzy.com` already in your SPF | DKIM CNAMEs only | `@fastdiscountfinder.com` | free tier | smaller provider |
| Brevo | nothing yet | 3 records above | `@fastdiscountfinder.com` | 300/day free | cheapest, most work up front |

All four still need a credential that only you hold. Nothing on this device can send:
`~/.secrets/brevo.env` is empty and every historical `xkeysib-` key found in old session logs
returns **401**; there is no SMTP/Resend/Mailgun/SendGrid cred and no mail client installed.

## Before pressing send

1. Replace `[[POSTAL-ADDRESS]]` in the footer with the real business address (CAN-SPAM; the
   preflight fails until this is a real address). Keep it in the `.txt` part too.
2. Sender must be an address at the authenticated domain — not a free mailbox spoofed as the domain.
3. Check Brevo's own review: campaigns that sell `.edu` credentials + verification bypasses are
   exactly what ESP acceptable-use teams reject. If Brevo blocks the campaign, the fallback is
   MailerSend/Selzy (Fix B) or your own SMTP — the HTML is provider-agnostic.
4. Send to a seed list first (Gmail, Outlook, Yahoo) and confirm inbox + no clipping; only then
   the real list. One bad blast on a fresh domain is unrecoverable.
