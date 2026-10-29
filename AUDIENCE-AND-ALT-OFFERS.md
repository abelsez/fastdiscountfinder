# Audience reality check + alternative monetisation

Pulled live from the Brevo account (API `v3`): 20 populated lists, 1,330 contacts, 100 campaigns
(75 sent, 24 drafts, several `suspended`). Everything below is measured, not assumed.

## 1. Who this list actually is

| fact | value | source |
|---|---|---|
| contacts | 1,330 | `GET /contacts` |
| biggest list | 28 `All Openers – Stylized Campaign` — 1,328 | `/contacts/lists` |
| list sent today | 32 `Openers 300 Oct 2026` — 300 (292 eligible, 8 blacklisted) | `#130` |
| free-mail share | **85 %** (229 Gmail of 300) | contacts in list 32 |
| actual `.edu` addresses | **1 of 300** | same |
| added 2023 / 2024 / unknown | 79 / 27 / 194 | `ADDED_TIME` attribute |
| detected country/city/region | **empty for all 300** | `_DETECTED_*` attributes |
| `FIRSTNAME` values | handles like `willdrody` | sample |
| today's engagement | 6.0 % opens · 1.1 % CTR · 0 bounces · 0 complaints | `#130` campaignStats |
| 12-send baseline | 26.6 % opens · 2.0 % CTR | campaigns #93–#130 |

**Conclusion:** this is not a student list. It is a *discount-seeker* list — people who wanted
student pricing but **do not have a .edu address** (1 in 300). That is precisely why they were
sold one. It is imported, handle-named, 85 % Gmail, with no detectable geography and no consent
trail. Treat it as cold, not warm.

## 2. Why the current offer is exhausted

The subjects across 100 campaigns are one product, rephrased: "custom name EDU email address",
"SheerID/completion verification", "Ivy League email (Harvard/Yale/Princeton)", "Prime Day
student discounts", "IKON Pass college discount", "YouTube Premium + Spotify". The best send in
the account (#110, 60.6 % opens) was a **status update**, not a pitch — the list responds to news,
not to another .edu ad.

## 3. Alternative offers that fit this psychology

Buying signal = "wants the discount without qualifying for it" → they respond to *access*,
*unlocking*, *free money*, not to education. Published/typical payouts (verify on each network —
most are Impact / CJ / Awin / PartnerStack gated):

| # | offer | network | payout | fit | risk |
|---|---|---|---|---|---|
| 1 | **Chime** (banking referral) | CJ / Impact / FlexOffers | **up to $75** per funded account; consumer referral $100 both sides | huge — cash incentive, no .edu needed | fintech compliance, KYC friction, disclosure |
| 2 | **Varo / Current** | private fintech networks | up to **$100** per funded account | same as above | same |
| 3 | **SoFi** | Impact | up to **$150**; $1,000+ on loan refi | medium (refi needs income, not students) | regulated finance |
| 4 | **NordVPN / Surfshark** | own/Impact | **40–100 %** first sale + 30 % recurring | strong: VPN = "unlock content you're geo-blocked from" — same emotion as .edu gating | none material |
| 5 | **Grammarly** | Impact/CJ | **~$20/sale**, 90-day cookie | strong: free→paid, students + writers, long cookie | none |
| 6 | **Perplexity Pro** | Dub | **$15–20** per Pro sub | strong: "AI access cheaper/students" angle | none |
| 7 | **Notion** | PartnerStack | up to **$50**/activated workspace + 20 % yr1 | medium (often paused for new affiliates) | none |
| 8 | **Coursera / Udemy** | Impact | **15–45 %** / **10–15 %** (7-day cookie) | medium: learning intent, but they wanted discounts not courses | low |
| 9 | **Airalo / Saily eSIM** | Impact / own | **~10 %** / creator terms ($50 payout floor) | medium: travel + students | low |
| 10 | **Temu / Shein** | own / Awin | Temu **5–35 % + $5–6/app install**, Shein **15 %** new-customer | very high EPC for discount-seekers | brand/reputation, and it is exactly what gets ESP accounts suspended |
| 11 | **BooksRun / BookScouter** | own / LinkTrust | **9 %** / **$1 flat** | low value per click | none |

**What I would actually run, in order:** NordVPN → Grammarly → Perplexity → Chime.
Reason: three of them convert without a credit check, all four pay $15–75, and each is a *new*
promise instead of the eleventh .edu email. Temu is the highest EPC but it is also the fastest way
to lose the Brevo account you just unblocked (the campaigns already suspended by Brevo review were
all aggressive-offer sends).

## 4. Which list gets which offer

| list | size | state | send |
|---|---|---|---|
| 30 `clickersaugust` | 194 | warmest (actual clicks) | Chime $100 referral — cash, no qualification |
| 22 `Iscariot clickers` | 194 | warm | NordVPN (unlock-geo angle) |
| 17 `Clickers 2026` | 147 | warm | Grammarly free→paid |
| 32 `Openers 300 Oct 2026` | 300 | opened #130 | Perplexity Pro |
| 31 `Greenlight Openers Never Clicked` | 110 | opens but no clicks | re-open with a status update (the #110 pattern) |
| 28 `All Openers – Stylized` | 1,328 | cold, superset | only after SPF is fixed + warmup; batch 50/day |

## 5. The economics, honestly

Current per-292-send result: 17 opens, 3 clicks, 0 revenue. At a $20 CPA and a **10 %**
click→conversion rate you need ~10 clicks for $20 — i.e. roughly **1,000 sents per $20**. The
constraint is not the offer, it is the 6 % open rate. Fix the inbox (SPF include, warmup, matching
from/landing domain) and the same list is worth ~4× more before changing a word of copy.

Priority order, non-negotiable:
1. `smartworld.press` SPF → add `include:spf.brevo.com` (DKIM already aligned).
2. Send the affiliate angles from a domain that matches the link domain.
3. Batch 50/day, 3 days, watch opens; only then scale.
4. Join 2 networks (Impact + CJ) — that single pair covers NordVPN, Grammarly, Coursera, Chime.

## 6. Three campaigns worth drafting next

| campaign | subject | offer | why it should beat 6 % |
|---|---|---|---|
| A | `Your .edu is gone — but the student price isn't` | NordVPN 2-yr (unlock geo-locked streaming) | hits the same "locked out" nerve with a product that needs no verification |
| B | `$100 to open a bank account (no .edu, no credit check)` | Chime referral | pure cash, zero qualification — the exact thing this list buys |
| C | `We got you a free month of AI (no student ID)` | Perplexity Pro | "access without qualifying" framing that has always worked for this list |

Each needs: affiliate disclosure line, postal address (537 Grand Blvd, San Mateo, CA 94401),
one-click unsubscribe, and the same preflight (`scripts/inbox-preflight.sh`) before sending.

---

## 7. Verified offers (free open-affiliate API, pulled 2026-10-29)

Source: `https://openaffiliate.dev/api/programs` (1,327 programs, no key needed). Filtered shortlist saved to
`affiliate-data/openaffiliate-shortlist.json`. Every row below carries the dataset's own `verified` flag and
`lastVerifiedAt` date — these are not blog-sourced numbers.

| program | commission | cookie | network | verified | sign-up |
|---|---|---|---|---|---|
| PureVPN | **up to 100 %** | 90 d | in-house | ✅ 2026-10-13 | `purevpn.com/affiliates/signup` |
| iTop VPN | 40–100 % by product | – | – | ✅ 2026-10-26 | `itopvpn.com/affiliate-solutions` |
| Surfshark | **40 %** + renewals | 30 d | own/Impact/CJ/Awin | ✅ 2026-10-13 | `surfshark.com/affiliate-signup` |
| MacPaw (CleanMyMac) | 35 % | **180 d** | Impact | ✅ 2026-10-13 | `macpaw.com/affiliate` |
| Boomerang | 40 % | 90 d | FirstPromoter | ✅ 2026-10-13 | `boomerangme.com/affiliate-program` |
| **Grammarly** | **$20/upgrade + $0.20/signup** | **90 d** | Impact | ✅ 2026-10-18 | `grammarly.com/affiliates` |
| xTiles | 30 % | – | PartnerStack | ✅ 2026-10-17 | `xtiles.app/en/affiliate/` |
| Consensus (AI research) | 30 % | – | PartnerStack | ✅ 2026-10-12 | PartnerStack listing |
| Prepostseo | 30 % + 10 % | 90 d | in-house | ✅ 2026-10-13 | `prepostseo.com/affiliate` |
| SciSummary | up to 80 % or $4 | – | Rewardful | ⚠️ unverified | `scisummary.com/affiliates` |
| Canva | up to $36/Pro sub | – | Impact | ⚠️ unverified | `canva.com/affiliates/` |
| Perplexity AI | $15–20/Pro sub | 30 d | Dub | ⚠️ unverified | `partners.dub.co/perplexity` |

**Not in the dataset — network-gated, must be applied for directly:** Chime ($75 CPA / $100 referral), SoFi
($150+, $1,000+ refi), Varo/Current ($100), Coursera (15–45 %), Udemy (10–15 %), Temu (5–35 % + $5–6/install),
Shein (15 %), Airalo (10 %), Ibotta ($2–5), Swagbucks ($1.76–2), Rakuten, BooksRun (9 %), BookScouter ($1).
Those figures come from published program pages / network listings, **not** from a verified feed — treat as
±, and confirm inside Impact/CJ before building a campaign around them.

### Why the verified column matters for this list
The three that verified *and* fit the "unlock access without qualifying" psychology are **Grammarly
($20, 90-day cookie)**, **Surfshark/PureVPN (40–100 %, VPN = unblocking — the same nerve as .edu gating)**,
and **Consensus/xTiles (30 % SaaS)**. The 90–180-day cookies matter more than headline rate here: this list
opens slowly (6 %), so a 30-day cookie loses most of the tail.
