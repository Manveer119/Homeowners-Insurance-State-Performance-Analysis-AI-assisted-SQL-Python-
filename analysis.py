"""
State performance & segmentation analysis for a synthetic homeowners book.

Steps:
  1. Load CSVs into an in-memory SQLite database.
  2. Run the SQL in /sql (drafted with AI assistance).
  3. Validate: data-quality checks + recompute every key metric independently
     in pandas and confirm it matches the SQL output.
  4. Size a rate-change scenario under explicit, stated assumptions.
  5. Save result tables and charts to /outputs.

Run:  python src/analysis.py
"""
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
DATA, SQL, OUT = ROOT / "data", ROOT / "sql", ROOT / "outputs"
CHARTS = OUT / "charts"
CHARTS.mkdir(parents=True, exist_ok=True)

NAVY, GREY, RED = "#1F3864", "#9AA5B1", "#C0392B"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


# ---------------------------------------------------------------- load
def load():
    quotes = pd.read_csv(DATA / "quotes.csv")
    policies = pd.read_csv(DATA / "policies.csv")
    claims = pd.read_csv(DATA / "claims.csv")
    con = sqlite3.connect(":memory:")
    for name, df in [("quotes", quotes), ("policies", policies), ("claims", claims)]:
        df.to_sql(name, con, index=False)
    return con, quotes, policies, claims


def run_sql(con, file):
    return pd.read_sql_query((SQL / file).read_text(), con)


# ---------------------------------------------------------------- validation
class Checks:
    def __init__(self):
        self.rows = []

    def add(self, name, passed, detail=""):
        self.rows.append({"check": name, "result": "PASS" if passed else "FAIL", "detail": detail})

    def report(self):
        df = pd.DataFrame(self.rows)
        df.to_csv(OUT / "validation_results.csv", index=False)
        print(df.to_string(index=False))
        if (df.result == "FAIL").any():
            raise SystemExit("Validation failed - do not use these results.")
        return df


def data_quality(chk, quotes, policies, claims):
    chk.add("Quote IDs unique", quotes.quote_id.is_unique)
    chk.add("Policy IDs unique", policies.policy_id.is_unique)
    chk.add("Every bound quote has exactly one policy",
            quotes.bound.sum() == len(policies) and policies.quote_id.isin(quotes.quote_id[quotes.bound == 1]).all(),
            f"bound={quotes.bound.sum():,}, policies={len(policies):,}")
    orphans = (~claims.policy_id.isin(policies.policy_id)).sum()
    chk.add("No orphan claims", orphans == 0, f"orphans={orphans}")
    chk.add("No missing values", not (quotes.isna().any().any() or policies.isna().any().any() or claims.isna().any().any()))
    merged = claims.merge(policies[["policy_id", "coverage_a", "effective_date"]], on="policy_id")
    chk.add("No claim exceeds Coverage A", (merged.incurred_loss <= merged.coverage_a).all())
    days = (pd.to_datetime(merged.loss_date) - pd.to_datetime(merged.effective_date)).dt.days
    chk.add("Loss dates fall within the 12-month term", days.between(0, 365).all())
    chk.add("Premiums and losses are positive",
            (policies.written_premium > 0).all() and (claims.incurred_loss > 0).all())


def reconcile(chk, sql_df, pandas_df, key, cols, label, tol=1e-3):
    m = sql_df.merge(pandas_df, on=key, suffixes=("_sql", "_pd"))
    chk.add(f"{label}: same row count", len(m) == len(sql_df) == len(pandas_df), f"{len(m)} rows")
    for c in cols:
        diff = (m[f"{c}_sql"] - m[f"{c}_pd"]).abs().max()
        chk.add(f"{label}: {c} matches pandas", diff <= tol, f"max abs diff={diff:.6f}")


def pandas_state(quotes, policies, claims):
    q = quotes.groupby("state").agg(quotes=("quote_id", "size"), binds=("bound", "sum"))
    q["quote_to_bind"] = q.binds / q.quotes
    p = policies.groupby("state").agg(policies=("policy_id", "size"),
                                      written_premium=("written_premium", "sum"),
                                      retention_rate=("renewed", "mean"))
    c = claims.merge(policies[["policy_id", "state"]], on="policy_id").groupby("state").agg(
        claims=("claim_id", "size"), incurred_loss=("incurred_loss", "sum"))
    df = q.join(p).join(c).fillna(0)
    df["loss_ratio"] = df.incurred_loss / df.written_premium
    return df.reset_index().round({"quote_to_bind": 4, "retention_rate": 4, "loss_ratio": 4,
                                   "written_premium": 2, "incurred_loss": 2})


def pandas_segment(policies, claims):
    ct = claims.groupby("policy_id").incurred_loss.sum().rename("incurred_loss")
    p = policies.join(ct, on="policy_id").fillna({"incurred_loss": 0})
    g = p.groupby(["roof_age_band", "coastal_zone"]).agg(policies=("policy_id", "size"),
                                                          written_premium=("written_premium", "sum"),
                                                          incurred_loss=("incurred_loss", "sum")).reset_index()
    g["loss_ratio"] = (g.incurred_loss / g.written_premium).round(4)
    return g.round({"written_premium": 2, "incurred_loss": 2})


# ---------------------------------------------------------------- scenario
def rate_scenario(policies, claims, state, rate_change, elasticities=(-0.5, -1.0, -1.5)):
    """
    Size a rate change for one state. Assumptions (stated, not derived from data):
      - New-business volume responds to price with the given elasticity.
      - Policies lost to the increase have the state's average loss cost (no adverse selection).
      - Rate applies to the full book in that state for one policy term.
    """
    p = policies[policies.state == state]
    losses = claims[claims.policy_id.isin(p.policy_id)].incurred_loss.sum()
    prem = p.written_premium.sum()
    rows = [{"scenario": "Current", "elasticity": None, "policies": len(p),
             "written_premium": prem, "incurred_loss": losses, "loss_ratio": losses / prem}]
    for e in elasticities:
        vol = 1 + e * rate_change
        rows.append({"scenario": f"+{rate_change:.0%} rate", "elasticity": e,
                     "policies": round(len(p) * vol),
                     "written_premium": prem * vol * (1 + rate_change),
                     "incurred_loss": losses * vol,
                     "loss_ratio": (losses * vol) / (prem * vol * (1 + rate_change))})
    return pd.DataFrame(rows).round(4)


# ---------------------------------------------------------------- charts
def charts(state_df, seg_df, chan_df):
    # 1. Loss ratio by state
    d = state_df.sort_values("loss_ratio")
    fig, ax = plt.subplots(figsize=(7, 4))
    colors = [RED if v > 0.65 else NAVY for v in d.loss_ratio]
    ax.barh(d.state, d.loss_ratio, color=colors)
    ax.axvline(0.65, color=GREY, ls="--", lw=1)
    ax.text(0.655, -0.6, "65% target", color=GREY, fontsize=8)
    for y, v in enumerate(d.loss_ratio):
        ax.text(v + 0.01, y, f"{v:.0%}", va="center", fontsize=8)
    ax.set_xlabel("Loss ratio (incurred loss / written premium)")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.set_title("Loss ratio by state", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(CHARTS / "loss_ratio_by_state.png", dpi=150); plt.close(fig)

    # 2. Growth matrix: conversion vs loss ratio, bubble = premium
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.scatter(state_df.loss_ratio, state_df.quote_to_bind,
               s=state_df.written_premium / state_df.written_premium.max() * 1500,
               color=NAVY, alpha=0.6)
    for _, r in state_df.iterrows():
        ax.annotate(r.state, (r.loss_ratio, r.quote_to_bind), ha="center", va="center", color="white", fontsize=8, fontweight="bold")
    ax.axvline(0.65, color=GREY, ls="--", lw=1)
    ax.axhline(state_df.binds.sum() / state_df.quotes.sum(), color=GREY, ls=":", lw=1)
    ax.set_xlabel("Loss ratio"); ax.set_ylabel("Quote-to-bind rate")
    ax.xaxis.set_major_formatter(PercentFormatter(1)); ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_title("Growth matrix: profitability vs. conversion (bubble = premium)", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(CHARTS / "growth_matrix.png", dpi=150); plt.close(fig)

    # 3. Loss ratio by roof age, coastal vs inland
    fig, ax = plt.subplots(figsize=(7, 4))
    bands = ["0-5", "6-10", "11-15", "16-20", "21+"]
    x = np.arange(len(bands)); w = 0.38
    for i, (cz, lab, col) in enumerate([(0, "Inland", NAVY), (1, "Coastal", RED)]):
        s = seg_df[seg_df.coastal_zone == cz].set_index("roof_age_band").reindex(bands)
        ax.bar(x + (i - 0.5) * w, s.loss_ratio, w, label=lab, color=col)
    ax.set_xticks(x, bands); ax.set_xlabel("Roof age (years)"); ax.set_ylabel("Loss ratio")
    ax.yaxis.set_major_formatter(PercentFormatter(1)); ax.axhline(0.65, color=GREY, ls="--", lw=1)
    ax.legend(frameon=False)
    ax.set_title("Loss ratio by roof age and coastal exposure", loc="left", fontweight="bold")
    fig.tight_layout(); fig.savefig(CHARTS / "loss_ratio_roof_coastal.png", dpi=150); plt.close(fig)

    # 4. Conversion by channel
    piv = chan_df.pivot(index="state", columns="channel", values="quote_to_bind")
    ax = piv.plot(kind="bar", figsize=(8, 4), color=[NAVY, GREY, RED], width=0.8)
    ax.set_ylabel("Quote-to-bind rate"); ax.set_xlabel("")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.set_title("Quote-to-bind by channel and state", loc="left", fontweight="bold")
    ax.legend(frameon=False, ncol=3); plt.xticks(rotation=0)
    plt.tight_layout(); plt.savefig(CHARTS / "conversion_by_channel.png", dpi=150); plt.close()


# ---------------------------------------------------------------- main
def main():
    con, quotes, policies, claims = load()
    state_df = run_sql(con, "01_state_performance.sql")
    seg_df = run_sql(con, "02_segment_roof_coastal.sql")
    chan_df = run_sql(con, "03_channel_by_state.sql")

    chk = Checks()
    data_quality(chk, quotes, policies, claims)
    reconcile(chk, state_df, pandas_state(quotes, policies, claims), "state",
              ["quotes", "binds", "quote_to_bind", "policies", "written_premium",
               "retention_rate", "claims", "incurred_loss", "loss_ratio"], "State scorecard")
    reconcile(chk, seg_df, pandas_segment(policies, claims), ["roof_age_band", "coastal_zone"],
              ["policies", "written_premium", "incurred_loss", "loss_ratio"], "Roof/coastal segments")
    chk.add("Segment premium ties to total book",
            abs(seg_df.written_premium.sum() - policies.written_premium.sum()) < 1)
    chk.add("Segment losses tie to total claims",
            abs(seg_df.incurred_loss.sum() - claims.incurred_loss.sum()) < 1)
    chk.add("Channel binds tie to total binds", chan_df.binds.sum() == quotes.bound.sum())
    chk.add("Roof bands returned in logical (not text) order",
            seg_df[seg_df.coastal_zone == 0].roof_age_band.tolist() == ["0-5", "6-10", "11-15", "16-20", "21+"])
    chk.report()

    worst = state_df.sort_values("loss_ratio", ascending=False).iloc[0].state
    scen = rate_scenario(policies, claims, worst, 0.08)

    state_df.to_csv(OUT / "state_scorecard.csv", index=False)
    seg_df.to_csv(OUT / "segment_roof_coastal.csv", index=False)
    chan_df.to_csv(OUT / "channel_by_state.csv", index=False)
    scen.to_csv(OUT / f"rate_scenario_{worst}.csv", index=False)
    charts(state_df, seg_df, chan_df)

    pd.set_option("display.width", 200)
    print("\nSTATE SCORECARD\n", state_df.to_string(index=False))
    print("\nROOF / COASTAL\n", seg_df.to_string(index=False))
    print("\nCHANNEL\n", chan_df.to_string(index=False))
    print(f"\nRATE SCENARIO ({worst})\n", scen.to_string(index=False))


if __name__ == "__main__":
    main()
