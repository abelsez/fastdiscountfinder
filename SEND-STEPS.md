# Send the campaign — manual steps (no API needed)

Reply-To on every path: **jmaclive101@gmail.com** (set in `.eml`, `brevo.env`, `brevo-smtp.env`).

## Path 1 — from your own phone mail app (30 seconds, in progress)

1. A Gmail/Outlook compose window was already opened by me, addressed to
   `jmaclive101@gmail.com`, with subject + full plain-text body prefilled
   (marketing campaigns cannot carry HTML through a `mailto:` intent — that is a client limit).
2. Tap **Send**. You now have a seed copy: check it did not land in Spam, and that the
   preheader/CTA text reads correctly.

## Path 2 — send the real thing from any desktop mail client (recommended, zero setup)

1. Download `campaign-send.eml` from `/storage/emulated/0/Download/` to a computer.
2. Open it:
   - **Outlook** — File → Open → select the `.eml` → it opens as a compose window (because of `X-Unsent: 1`).
   - **Thunderbird** — double-click, then Message → Edit As New.
   - **Gmail web** — drag the `.eml` file onto the inbox, or use *Settings → Advanced → import*.
3. Put your list in **Bcc** (batch 50/day for a fresh domain).
4. Check the footer has your real postal address before sending (the placeholder was stripped,
   so add your address line manually — US CAN-SPAM requires it).
5. Send.

## Path 3 — Brevo web UI (uses Brevo's unsubscribe/tracking/stats)

1. app.brevo.com → **Campaigns** → **Create a campaign** → *Email*.
2. Recipients: pick your list (this is the "audience").
3. Content: choose **Paste your code** / *Import HTML* → paste all of
   `email/edu-custom-2026-10-29.html` (or upload the file).
4. Subject: `Your custom .edu email + 200+ student discounts`
   Preview text: `Cut $2,000+ off your yearly subscriptions. Setup takes 2 minutes, delivered in 24h.`
5. Sender: a **verified** sender at an authenticated domain → **Reply-To: jmaclive101@gmail.com**.
6. Send a **test** to `jmaclive101@gmail.com` first, confirm inbox + rendering.
7. **Send now** (or schedule).

## Path 4 — API (fastest once the account stops blocking this IP)

1. app.brevo.com/security/authorised_ips → *API keys* row → **Deactivate for API**
   (or add `102.213.179.0/24`).
2. `cd ~/fastdiscountfinder && ./scripts/go-live.sh` → prints account, authenticated domains,
   verified senders, lists + subscriber counts, runs the preflight, creates the **draft**.
3. If preflight passes: set `BREVO_ALLOW_SEND=yes` in `~/.secrets/brevo.env`, then
   `./scripts/go-live.sh --send`.

## Path 5 — SMTP key + contact export (bypasses the IP allowlist entirely)

1. Brevo → Settings → **SMTP & API** → **SMTP** tab → **Generate a new SMTP key**.
2. Brevo → **Contacts** → **Export contacts (CSV)** → save as
   `/storage/emulated/0/Download/subscribers.csv`.
3. Fill `~/.secrets/brevo-smtp.env`:
   ```
   BREVO_SMTP_KEY=xsmtpsib-...
   BREVO_SMTP_USER=<SMTP login shown next to the key>
   BREVO_SENDER_EMAIL=<verified sender>
   BREVO_REPLY_TO=jmaclive101@gmail.com
   BREVO_ALLOW_SEND=yes
   ```
4. Seed first:
   `./scripts/smtp-send.py --subject "Your custom .edu email + 200+ student discounts" --html email/edu-custom-2026-10-29.html --txt email/edu-custom-2026-10-29.txt --seed`
5. Then the list (needs a `--csv` reader — add it when the export exists):
   same command with `--to` per address, batches of 50/day.

## Pre-send checklist (all verifiable locally)

```bash
cd ~/fastdiscountfinder
./scripts/inbox-preflight.sh <sending-domain> email/edu-custom-2026-10-29.html \
  "Your custom .edu email + 200+ student discounts"
# exit 0 = clean; anything else lists the blocking item and its fix
```
- [ ] real postal address in the footer
- [ ] sender domain shows DKIM (`./scripts/email-auth.sh <domain>` → `DKIM  : … -> …`)
- [ ] seed landed in the inbox, not Spam
- [ ] unsubscribe link works (Brevo injects it; the `.eml` carries `List-Unsubscribe` one-click)
