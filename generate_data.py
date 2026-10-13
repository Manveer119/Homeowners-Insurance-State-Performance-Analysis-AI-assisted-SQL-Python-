"""
Generate a SYNTHETIC homeowners insurance dataset (quotes, policies, claims).

No real company or customer data is used. Risk patterns are built in on purpose
(e.g., older roofs and coastal homes carry higher loss costs) so the analysis has
realistic signals to find. Seeded for reproducibility.

Run:  python src/generate_data.py
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
N_QUOTES = 60_000
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data"
OUT.mkdir(exist_ok=True)

# State profiles: share of quote volume, base premium, base annual claim frequency,
# share of homes in coastal/catastrophe-exposed zones, and a market competitiveness
# factor (higher = harder to win the quote).
STATES = {
    #      share  base_prem  freq   coastal  competition
    "FL": (0.22, 3200, 0.070, 0.55, 1.10),
    "TX": (0.18, 2600, 0.085, 0.20, 1.05),
    "LA": (0.08, 2900, 0.075, 0.45, 1.00),
    "SC": (0.09, 2100, 0.050, 0.30, 0.95),
    "NC": (0.11, 1800, 0.045, 0.20, 0.95),
    "GA": (0.10, 1900, 0.055, 0.05, 1.00),
    "VA": (0.12, 1500, 0.035, 0.10, 1.15),
    "AZ": (0.10, 1600, 0.040, 0.00, 1.00),
}
CHANNELS = {"Direct": 0.50, "Agent": 0.35, "Partner": 0.15}
CHANNEL_BIND = {"Direct": 0.24, "Agent": 0.30, "Partner": 0.18}
ROOF_BANDS = ["0-5", "6-10", "11-15", "16-20", "21+"]
ROOF_P = [0.20, 0.25, 0.22, 0.18, 0.15]
ROOF_FREQ = {"0-5": 0.70, "6-10": 0.85, "11-15": 1.00, "16-20": 1.35, "21+": 1.80}
ROOF_PREM = {"0-5": 0.92, "6-10": 0.97, "11-15": 1.00, "16-20": 1.08, "21+": 1.15}
PERILS = {"Wind/Hail": 0.38, "Water": 0.30, "Fire": 0.10, "Theft": 0.10, "Other": 0.12}
PERIL_SEV = {"Wind/Hail": 14_000, "Water": 11_000, "Fire": 45_000, "Theft": 5_000, "Other": 7_000}


def main() -> None:
    states = list(STATES)
    st = rng.choice(states, N_QUOTES, p=[STATES[s][0] for s in states])
    ch = rng.choice(list(CHANNELS), N_QUOTES, p=list(CHANNELS.values()))
    roof = rng.choice(ROOF_BANDS, N_QUOTES, p=ROOF_P)
    coastal = np.array([rng.random() < STATES[s][3] for s in st])
    coverage_a = rng.lognormal(np.log(320_000), 0.35, N_QUOTES).round(-3)
    quote_date = pd.to_datetime("2024-01-01") + pd.to_timedelta(rng.integers(0, 366, N_QUOTES), unit="D")

    base = np.array([STATES[s][1] for s in st])
    prem = (base * (coverage_a / 320_000) ** 0.8
            * np.array([ROOF_PREM[r] for r in roof])
            * np.where(coastal, 1.35, 1.0)
            * rng.lognormal(0, 0.10, N_QUOTES)).round(2)

    # Bind probability: channel baseline, worse when the market is competitive or price is high
    comp = np.array([STATES[s][4] for s in st])
    p_bind = (np.array([CHANNEL_BIND[c] for c in ch]) / comp
              * np.clip((base / prem) ** 0.6, 0.5, 1.3))
    bound = rng.random(N_QUOTES) < np.clip(p_bind, 0.02, 0.6)

    quotes = pd.DataFrame({
        "quote_id": [f"Q{i:06d}" for i in range(N_QUOTES)],
        "quote_date": quote_date.date,
        "state": st, "channel": ch, "roof_age_band": roof,
        "coastal_zone": coastal.astype(int), "coverage_a": coverage_a,
        "quoted_premium": prem, "bound": bound.astype(int),
    })

    pol = quotes[quotes.bound == 1].copy().reset_index(drop=True)
    pol["policy_id"] = [f"P{i:06d}" for i in range(len(pol))]
    pol["effective_date"] = pol["quote_date"]
    pol["written_premium"] = pol["quoted_premium"]
    renew_p = 0.86 - 0.10 * (pol["channel"] == "Partner") - 0.04 * (pol["state"] == "FL")
    pol["renewed"] = (rng.random(len(pol)) < renew_p).astype(int)
    policies = pol[["policy_id", "quote_id", "state", "channel", "roof_age_band", "coastal_zone",
                    "coverage_a", "effective_date", "written_premium", "renewed"]]

    # Claims over a 12-month term
    freq = (np.array([STATES[s][2] for s in policies.state])
            * np.array([ROOF_FREQ[r] for r in policies.roof_age_band])
            * np.where(policies.coastal_zone == 1, 1.6, 1.0))
    n_claims = rng.poisson(freq)
    rows = []
    cid = 0
    for idx in np.nonzero(n_claims)[0]:
        p = policies.iloc[idx]
        for _ in range(n_claims[idx]):
            peril = rng.choice(list(PERILS), p=list(PERILS.values()))
            sev = PERIL_SEV[peril] * (p.coverage_a / 320_000) ** 0.5 * rng.lognormal(0, 0.8)
            if p.coastal_zone and peril == "Wind/Hail":
                sev *= 1.7
            loss_date = pd.to_datetime(p.effective_date) + pd.Timedelta(days=int(rng.integers(0, 365)))
            rows.append((f"C{cid:06d}", p.policy_id, loss_date.date(), peril, round(min(sev, p.coverage_a), 2)))
            cid += 1
    claims = pd.DataFrame(rows, columns=["claim_id", "policy_id", "loss_date", "peril", "incurred_loss"])

    quotes.to_csv(OUT / "quotes.csv", index=False)
    policies.to_csv(OUT / "policies.csv", index=False)
    claims.to_csv(OUT / "claims.csv", index=False)
    print(f"quotes={len(quotes):,} policies={len(policies):,} claims={len(claims):,}")


if __name__ == "__main__":
    main()
