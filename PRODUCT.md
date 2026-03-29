# LeakLock - Revenue Leak Detection SaaS

## Product Overview

**Product Name:** LeakLock  
**Tagline:** Find hidden revenue leaks. Pay only when we find your money.  
**Value Proposition:** Automated detection of 7 common billing leakage patterns that cost businesses 5-15% of revenue. Free scan, results-first, no risk.

---

## Target Customers

### Primary Verticals
- **Dental Practices** — Lose $30K-$60K/year to insurance billing errors, write-off leakage, and failed payment neglect. Use Dentrix, Eaglesoft, Open Dental.
- **Medical Practices** — EHR billing exports riddled with underbilled procedures, credit memo overissuance, and scope creep.
- **SaaS Companies** — Stripe billing leakage: discount drift, usage underbilling, renewal erosion.
- **Law Firms** — Time billing leakage, scope creep on flat-fee engagements, write-down amnesia.
- **Contractors & Service Businesses** — Change order amnesia, unapproved write-downs, retainage leakage.

### Customer Profile
- **Revenue:** $100K - $5M/year
- **Pain:** They know they're losing money; they don't know where.
- **Trigger:** CPA audit quoted $5K+. We're free until we find something.

---

## Pricing Model

### How We Get Paid

LeakLock operates on a **results-first** model. We don't get paid until your business wins.

---

### Step 1 — Free Scan (Always Free)
- Upload any CSV billing export
- No account required
- No credit card
- See your leaks in 60 seconds
- **Cost: $0. Forever.**

---

### Step 2 — Recovery Fee (10% of What We Find)
- After the free scan, if you want to pursue recovery, we charge **10% of the leakage amount recovered** in the first 90 days.
- Example: We find $40,000 in billing leakage → you recover it → we earn $4,000.
- **No recovery = no charge.** You can walk away with the report for free.
- This is the only risk-aligned fee model in revenue leak detection.

**Comparison:**
| Method | Cost | Risk |
|--------|------|------|
| CPA billing audit | $3,000-$7,000 flat | You pay whether they find anything |
| LeakLock Recovery | 10% of what's found | $0 if we find nothing |

---

### Step 3 — Guardian Retainer (Ongoing Protection)
After the 90-day recovery period, keep LeakLock running for continuous monitoring:

| Plan | Price | Who It's For |
|------|-------|-------------|
| **Guardian Small** | $149/mo | <$500K/yr revenue |
| **Guardian Pro** | $349/mo | $500K-$5M/yr revenue |

**Guardian includes:**
- Continuous monitoring (daily scans)
- Monthly leak report
- Webhook alerts (Slack, email)
- 12-month history + trend analysis
- Pattern library updates as new leak types emerge

---

## The Business Math

**15 dental clients:**
- Recovery fees: 15 × $4,000 avg = **$60,000 one-time**
- Monthly retainer: 15 × $349/mo = **$5,235/month recurring**
- Annual retainer run rate: **$62,820/year**
- Year 1 total: **$122,820**

Nobody walks away from found money. That's why this compounds.

---

## The 7 Leakage Patterns

1. **Failed Payment Neglect** — Failed charges never retried. Money left on the table indefinitely.
2. **Scope Creep** — Services delivered without invoicing. The work happened; the billing didn't.
3. **Contract Term Amnesia** — Legacy pricing from expired contracts still applied months later.
4. **Credit Memo Overissuance** — Excessive credits issued without valid clinical or business justification.
5. **Discount Drift** — Gradual unauthorized expansion of discounts over time.
6. **Usage Underbilling** — Usage-based charges undercounted or not captured.
7. **Renewal Erosion** — Downgrades and silent cancellations at renewal.

---

## Dental-Specific Patterns

Dental practices have distinct billing structures. LeakLock maps universal patterns to dental-specific manifestations:

- **Failed Payment Neglect** → Patient co-pays not collected, insurance EFT failures ignored
- **Scope Creep** → Procedures completed but not billed (hygienist upcoding in reverse)
- **Contract Term Amnesia** → Old PPO fee schedules applied to updated insurance contracts
- **Credit Memo Overissuance** → Write-offs that weren't clinically warranted

---

## Go-to-Market

### Inbound (No Human Outreach)
1. **Google SEO** — "dental billing errors", "medical billing leakage", "revenue leak detection"
2. **Dental Practice Directories** — Dentistry Today, DentalTown
3. **SaaS Directories** — G2, Capterra, SaaShub (for SaaS vertical)
4. **Product Hunt** — Launch campaign
5. **Stripe App Marketplace** — For SaaS/Stripe vertical

### Landing Pages by Vertical
- `/dental` — Dental-specific landing page (live)
- `/medical` — Coming soon
- `/saas` — Coming soon
- `/legal` — Coming soon

---

## Technical Architecture

- **Database:** PostgreSQL `nexus` (saas_customers, saas_plans, saas_detected_leaks tables)
- **Connectors:** CSV upload (any billing export format), Stripe Connect (SaaS vertical)
- **Scheduling:** LaunchAgent for daily scans (Guardian Retainer customers)
- **Dashboard:** Flask app, inline CSS, no external dependencies
- **Auth:** Secret token per customer

---

## Demo Status

✅ Seeded with 12 billing events  
✅ 7 patterns defined in domain  
✅ Scanner ready for demo run  
✅ Pricing updated to recovery model  
✅ Dental landing page live at /dental
