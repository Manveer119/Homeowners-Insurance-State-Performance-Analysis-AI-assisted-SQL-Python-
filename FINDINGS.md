# Findings & Recommendations

**Scope:** 2024 synthetic homeowners book, 8 states, 60,000 quotes, 14,046 policies, $35.2M written premium.
**Book average:** 23.4% quote-to-bind, 53.1% loss ratio.

## State scorecard

| State | Written premium | Quote-to-bind | Retention | Loss ratio | Claims / 100 policies |
|---|---:|---:|---:|---:|---:|
| FL | $10.41M | 20.9% | 81.0% | 54.2% | 9.4 |
| TX | $6.77M | 22.9% | 86.1% | **66.3%** | 10.2 |
| LA | $3.64M | 22.9% | 85.1% | 58.9% | 10.2 |
| NC | $3.34M | 26.3% | 85.8% | 50.5% | 5.7 |
| SC | $3.29M | 26.1% | 86.7% | 42.8% | 5.3 |
| GA | $2.88M | 24.6% | 85.7% | 39.6% | 4.5 |
| VA | $2.45M | 22.0% | 85.3% | 46.3% | 3.6 |
| AZ | $2.39M | 24.9% | 85.3% | 42.7% | 4.5 |

## Recommendations

### 1. Review Texas rate adequacy
Texas is the only state above the 65% target. The cause is frequency (10.2 claims per 100 policies, versus 3.6–5.7 in the profitable states) rather than severity: Texas's average claim ($18.0K) is in line with other states, and its peril mix matches the book. Too many claims, not unusually large claims, is the problem, which points to a base rate that's too low for the state's claim frequency.

**+8% rate scenario (assumed elasticity, no adverse selection):**

| Elasticity | Policies | Written premium | Change in premium | Loss ratio |
|---:|---:|---:|---:|---:|
| Current | 2,454 | $6.77M | — | 66.3% |
| −0.5 | 2,356 | $7.02M | +3.7% | 61.4% |
| −1.0 | 2,258 | $6.72M | −0.6% | 61.4% |
| −1.5 | 2,160 | $6.43M | −5.0% | 61.4% |

The rate change brings Texas under target in every case. Whether premium grows or shrinks depends on how price-sensitive Texas customers are. The loss ratio is the same across elasticities only because the model assumes lost policies are average risks; if the customers who leave are the better risks, the real improvement would be smaller. Validating elasticity against actual quote data is the next step.

### 2. Tighten underwriting on coastal homes with 21+ year roofs
This segment runs a 108% loss ratio: 448 policies paying out more in claims than they bring in. Loss ratio rises with roof age in both coastal and inland homes, and the coastal effect is sharpest on the oldest roofs. Options to evaluate:
- Require a roof inspection or a roof replacement date at quote
- Use actual cash value (ACV) settlement for older roofs instead of replacement cost
- Add a roof-age surcharge in coastal zones

### 3. Prioritize growth in GA, SC, AZ, and NC
All four run loss ratios of 40–51% and convert above the book average. They have room to grow without hurting profitability: marketing spend, agent recruitment, or targeted price decreases in segments where loss experience supports it.

### 4. Investigate Virginia price competitiveness
Virginia's 46% loss ratio is the 4th-best in the book, but its 22.0% conversion is below average. Profitable but under-converting usually means the price is above competitors. A competitive rate comparison would show whether a modest decrease could add volume at an acceptable loss ratio.

### 5. Review the Partner channel
Partner has the lowest conversion in every state (14.8–18.4%) and the lowest retention (72–80%, versus roughly 84–90% for Agent and Direct). Before investing more in Partner, check lead quality and pricing at the point of sale.

## Caveats
- Synthetic data; patterns are illustrative.
- Small claim counts (58 in VA, 67 in GA) make state loss ratios directional.
- Premium treated as fully earned; no loss development or catastrophe load.
- Elasticity values are assumptions chosen to show sensitivity, not estimates.
