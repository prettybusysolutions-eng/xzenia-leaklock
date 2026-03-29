# LeakLock Demo Report
Generated: 2026-03-25 23:37:31

## Summary
- **Customers Scanned:** 4
- **Total Estimated Revenue at Risk:** $34,100
- **Leaks Detected:** 6 (across 4 patterns)

## Demo Data Results

### Customer: cus_002 (Pro Plan)
| Pattern | Amount | Confidence | Severity |
|---------|--------|-------------|----------|
| Renewal Erosion | $21,000 | 82% | HIGH |

### Customer: cus_003 (Starter Plan)
| Pattern | Amount | Confidence | Severity |
|---------|--------|-------------|----------|
| Credit Memo Overissuance | $1,300 | 70% | MEDIUM |

### Customer: cus_004 (Enterprise Plan)
| Pattern | Amount | Confidence | Severity |
|---------|--------|-------------|----------|
| Usage Underbilling | $2,700 | 65% | HIGH |
| Renewal Erosion | $4,800 | 82% | HIGH |

### Customer: cus_001 (Starter Plan)
| Pattern | Amount | Confidence | Severity |
|---------|--------|-------------|----------|
| Failed Payment Neglect | $4,300 | 88% | HIGH |

## Patterns Detected

1. **Failed Payment Neglect** - Unrecovered failed charges
2. **Renewal Erosion** - Downgrades/cancellations at renewal
3. **Credit Memo Overissuance** - Excessive refunds
4. **Usage Underbilling** - Missing metered billing

## Next Steps

1. Launch dashboard at `http://localhost:5000/dashboard/<customer_id>?token=<secret_token>`
2. Configure Stripe webhook endpoint
3. Submit to Stripe App Marketplace
4. Deploy to production

---
*LeakLock v0.1 - Revenue Leak Detection SaaS*