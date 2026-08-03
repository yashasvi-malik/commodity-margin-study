#!/usr/bin/env python3
"""
Commodity-to-Margin Sensitivity Study
India Auto-Ancillaries  |  Steel · Aluminium · Copper  →  OPM
Q1 2018 – Q4 2024  (28 quarters)

Research question:
  How do moves in steel, aluminium, and copper prices transmit
  into operating profit margins (OPM) of Indian auto-ancillary firms,
  and how many quarters does that transmission take?

Companies: Suprajit Engineering  |  Gabriel India
           Endurance Technologies  |  Sundram Fasteners

Run:  python analysis.py
Outputs: charts/ directory  +  terminal summary

NOTE: Data files in ../data/ currently hold PLACEHOLDER values.
Replace them with real data before drawing conclusions.
Follow ../data/data_entry_guide.md for step-by-step instructions.
"""

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import matplotlib.patches as mpatches
from scipy import stats
import warnings
import os
import sys

warnings.filterwarnings('ignore')
pd.set_option('display.float_format', '{:.3f}'.format)
pd.set_option('display.max_columns', 20)
pd.set_option('display.width', 120)


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION  — edit material weights after checking annual reports
# ═══════════════════════════════════════════════════════════════════════════════

# Weights should reflect actual RM cost breakdown from annual reports.
# These are estimates — verify from the RM section of each firm's annual report.
# The code normalises so they do not need to sum to 1.
MATERIAL_WEIGHTS = {
    'suprajit':  {'steel': 0.35, 'aluminium': 0.15, 'copper': 0.40},
    'gabriel':   {'steel': 0.50, 'aluminium': 0.35, 'copper': 0.10},
    'endurance': {'steel': 0.20, 'aluminium': 0.65, 'copper': 0.08},
    'sundram':   {'steel': 0.68, 'aluminium': 0.10, 'copper': 0.12},
}

FIRM_LABELS = {
    'suprajit':  'Suprajit Engineering',
    'gabriel':   'Gabriel India',
    'endurance': 'Endurance Technologies',
    'sundram':   'Sundram Fasteners',
}

FIRM_COLORS = {
    'suprajit':  '#2E75B6',
    'gabriel':   '#C00000',
    'endurance': '#375623',
    'sundram':   '#BF8F00',
}

FIRMS  = list(MATERIAL_WEIGHTS.keys())
METALS = ['steel', 'aluminium', 'copper']
MAX_LAG = 4   # test lags 0 → 4 quarters
ALPHA   = 0.10  # 10% significance level (justified for n ≈ 28)

# ── Paths ──────────────────────────────────────────────────────────────────────
ROOT   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA   = os.path.join(ROOT, 'data')
CHARTS = os.path.join(ROOT, 'charts')
os.makedirs(CHARTS, exist_ok=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def rebase_100(series: pd.Series) -> pd.Series:
    """Rebase a price series so first non-NaN value = 100."""
    first = series.dropna().iloc[0]
    return series / first * 100


def weighted_cost_index(prices: pd.DataFrame, weights: dict) -> pd.Series:
    """
    Build a firm-specific weighted commodity cost index.
    Each metal is rebased to 100 at the start of the sample, then
    combined using the firm's material-mix weights (normalised to sum to 1).
    """
    total_w = sum(weights[m] for m in METALS if m in prices.columns)
    idx = pd.Series(0.0, index=prices.index)
    for metal in METALS:
        if metal in prices.columns and metal in weights:
            w = weights[metal] / total_w
            idx += w * rebase_100(prices[metal])
    return idx


def yoy_growth(series: pd.Series) -> pd.Series:
    """Year-on-year % change (4-quarter lag)."""
    return series.pct_change(4) * 100


def lag_correlations(y: pd.Series, x: pd.Series, max_lag: int = 4) -> dict:
    """
    Pearson correlation between y and x lagged 0..max_lag quarters.
    Returns {lag: correlation}.
    The most negative correlation is the 'best' lag for a cost–margin squeeze.
    """
    corrs = {}
    for lag in range(max_lag + 1):
        df = pd.concat([y, x.shift(lag)], axis=1).dropna()
        if len(df) >= 5:
            corrs[lag] = df.iloc[:, 0].corr(df.iloc[:, 1])
        else:
            corrs[lag] = np.nan
    return corrs


def optimal_lag(corr_dict: dict) -> int:
    """Return the lag with the most negative correlation."""
    valid = {k: v for k, v in corr_dict.items() if not np.isnan(v)}
    return min(valid, key=lambda k: valid[k])


def ols_full(y: pd.Series, X: pd.DataFrame) -> dict | None:
    """
    OLS regression with t-statistics, p-values, and 95% confidence intervals.
    Uses numpy directly — no statsmodels required.
    Applies HC1 heteroskedasticity-robust standard errors.

    Parameters
    ----------
    y : outcome series
    X : predictor DataFrame (constant NOT included — added here)

    Returns
    -------
    dict with keys:
        n, r2, adj_r2, dof, coefs
        coefs[varname]: coef, se, tstat, pval, ci_lo, ci_hi, significant
    """
    df = pd.concat([y, X], axis=1).dropna()
    if len(df) < max(8, X.shape[1] + 3):
        return None

    n = len(df)
    y_arr  = df.iloc[:, 0].values.astype(float)
    X_cols = list(df.columns[1:])
    X_arr  = df.iloc[:, 1:].values.astype(float)
    Xc     = np.column_stack([np.ones(n), X_arr])   # add constant
    k      = Xc.shape[1]

    # OLS estimate
    try:
        beta, _, _, _ = np.linalg.lstsq(Xc, y_arr, rcond=None)
    except np.linalg.LinAlgError:
        return None

    y_hat     = Xc @ beta
    residuals = y_arr - y_hat

    # HC1 robust variance (White with df correction)
    XtX_inv = np.linalg.pinv(Xc.T @ Xc)
    meat    = np.zeros((k, k))
    for i in range(n):
        xi   = Xc[i:i+1, :].T
        ei2  = (residuals[i] ** 2) * (n / (n - k))    # HC1 scale
        meat += ei2 * (xi @ xi.T)
    cov_robust = XtX_inv @ meat @ XtX_inv

    se    = np.sqrt(np.maximum(np.diag(cov_robust), 0.0))
    t_arr = beta / se
    dof   = n - k
    p_arr = 2.0 * (1.0 - stats.t.cdf(np.abs(t_arr), df=dof))
    t_crit = stats.t.ppf(0.975, df=dof)
    ci_lo  = beta - t_crit * se
    ci_hi  = beta + t_crit * se

    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y_arr - y_arr.mean()) ** 2))
    r2     = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    adj_r2 = 1.0 - (1.0 - r2) * (n - 1) / (n - k) if n > k else 0.0

    varnames = ['const'] + X_cols
    coefs = {}
    for i, nm in enumerate(varnames):
        coefs[nm] = {
            'coef': beta[i], 'se': se[i], 'tstat': t_arr[i],
            'pval': p_arr[i], 'ci_lo': ci_lo[i], 'ci_hi': ci_hi[i],
            'significant': p_arr[i] < ALPHA,
        }

    return {'n': n, 'r2': r2, 'adj_r2': adj_r2, 'dof': dof, 'coefs': coefs}


def sig_star(pval: float) -> str:
    if pval < 0.01:  return '***'
    if pval < 0.05:  return '**'
    if pval < 0.10:  return '*'
    return ''


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ═══════════════════════════════════════════════════════════════════════════════

def load_data():
    req = {
        'commodity_prices': os.path.join(DATA, 'commodity_prices.csv'),
        'quarterly_margins': os.path.join(DATA, 'quarterly_margins.csv'),
    }
    for name, path in req.items():
        if not os.path.exists(path):
            sys.exit(f"\n  ERROR: {path} not found.\n"
                     f"  Follow data/data_entry_guide.md to enter real data.\n")

    comm = pd.read_csv(req['commodity_prices'],
                       comment='#', index_col='quarter')
    margins = pd.read_csv(req['quarterly_margins'],
                          comment='#', index_col='quarter')

    rev_path = os.path.join(DATA, 'revenue_quarterly.csv')
    rev = (pd.read_csv(rev_path, comment='#', index_col='quarter')
           if os.path.exists(rev_path) else None)

    # Load material weights from CSV (overrides hard-coded values if present)
    weights_path = os.path.join(DATA, 'material_mix_weights.csv')
    weights = dict(MATERIAL_WEIGHTS)  # copy defaults
    if os.path.exists(weights_path):
        wdf = pd.read_csv(weights_path, comment='#')
        for _, row in wdf.iterrows():
            firm = row['firm']
            if firm in FIRMS:
                weights[firm] = {
                    'steel':     float(row.get('steel', weights[firm]['steel'])),
                    'aluminium': float(row.get('aluminium', weights[firm]['aluminium'])),
                    'copper':    float(row.get('copper', weights[firm]['copper'])),
                }

    return comm, margins, rev, weights


# ═══════════════════════════════════════════════════════════════════════════════
# ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def run_analysis():
    print("\n" + "═" * 72)
    print("  COMMODITY → MARGIN SENSITIVITY STUDY")
    print("  India Auto-Ancillaries  |  Q1 2018 – Q4 2024")
    print("═" * 72)

    comm, margins, rev, weights = load_data()

    print(f"\n  Loaded {len(comm)} quarters  "
          f"({comm.index[0]} → {comm.index[-1]})")
    print(f"  Metals : {', '.join(c for c in comm.columns)}")
    print(f"  Firms  : {', '.join(FIRM_LABELS[f] for f in FIRMS)}")
    print(f"\n  NOTE: currently running on PLACEHOLDER data.")
    print("  Replace files in data/ with real investing.com + screener.in data.\n")

    # ── 1. Build firm-specific weighted cost indices ─────────────────────────
    firm_idx = {f: weighted_cost_index(comm, weights[f]) for f in FIRMS}
    sector_idx  = pd.concat(firm_idx.values(), axis=1).mean(axis=1)
    sector_idx.name = 'sector_idx'

    firm_opm = {f: margins[f] for f in FIRMS if f in margins.columns}
    sector_opm = margins[[f for f in FIRMS if f in margins.columns]].mean(axis=1)
    sector_opm.name = 'sector_opm'

    # ── 2. Revenue growth ────────────────────────────────────────────────────
    firm_rev_gr = {}
    sector_rev_gr = None
    if rev is not None:
        for f in FIRMS:
            col = f if f in rev.columns else f + '_rev'
            if col in rev.columns:
                firm_rev_gr[f] = yoy_growth(rev[col])
        if firm_rev_gr:
            sector_rev_gr = pd.concat(
                [rev[c] for c in rev.columns if c in FIRMS], axis=1
            ).mean(axis=1).pipe(yoy_growth)

    # ── 3. Sector lag analysis ───────────────────────────────────────────────
    sector_lag_corrs = lag_correlations(sector_opm, sector_idx, MAX_LAG)
    best_lag_sector  = optimal_lag(sector_lag_corrs)

    print("─" * 72)
    print("  A. SECTOR LAG ANALYSIS")
    print("─" * 72)
    print(f"\n  Correlation  (sector OPM  vs  weighted cost index  +  N quarters):\n")
    for lag, corr in sector_lag_corrs.items():
        mark = " ◀ strongest" if lag == best_lag_sector else ""
        print(f"      Lag {lag}Q :  {corr:+.3f}{mark}")
    print(f"\n  → Strongest (most negative) correlation at lag {best_lag_sector}Q.")
    print("    This is determined by the data, not pre-assumed.\n")

    # ── 4. Per-firm lag analysis ─────────────────────────────────────────────
    firm_lag_corrs_all = {}
    firm_best_lags     = {}
    print("─" * 72)
    print("  B. PER-FIRM LAG ANALYSIS")
    print("─" * 72)
    print(f"\n  {'Firm':<28}  {'Lag 0':>7} {'Lag 1':>7} {'Lag 2':>7} "
          f"{'Lag 3':>7} {'Lag 4':>7}  {'Best lag':>9}")
    print("  " + "─" * 72)
    for f in FIRMS:
        if f not in firm_opm:
            continue
        lc = lag_correlations(firm_opm[f], firm_idx[f], MAX_LAG)
        firm_lag_corrs_all[f] = lc
        firm_best_lags[f] = optimal_lag(lc)
        corr_row = '  '.join(f'{lc.get(l, np.nan):+.3f}' for l in range(MAX_LAG + 1))
        print(f"  {FIRM_LABELS[f]:<28}  {corr_row}   {firm_best_lags[f]}Q")

    # ── 5. Sector regression ─────────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("  C. SECTOR REGRESSION  (HC1 robust standard errors)")
    print("─" * 72)

    x_cost = sector_idx.shift(best_lag_sector).rename('cost_idx')

    # Model 1: OPM ~ cost index (no control)
    res1 = ols_full(sector_opm, pd.DataFrame(x_cost))

    # Model 2: OPM ~ cost index + revenue growth (control)
    res2 = None
    if sector_rev_gr is not None:
        X2 = pd.concat([x_cost, sector_rev_gr.rename('rev_growth')], axis=1)
        res2 = ols_full(sector_opm, X2)

    def print_model(label, res, varname='cost_idx'):
        if res is None:
            print(f"  {label}: insufficient data")
            return
        c = res['coefs'][varname]
        print(f"\n  {label}")
        print(f"    Observations     : {res['n']}")
        print(f"    Lag applied      : {best_lag_sector}Q")
        print(f"    Coefficient      : {c['coef']:+.4f} pp per unit cost rise")
        print(f"    Std error (HC1)  : {c['se']:.4f}")
        print(f"    t-statistic      : {c['tstat']:+.3f}")
        print(f"    p-value          : {c['pval']:.4f}  {sig_star(c['pval'])}  "
              f"({'SIGNIFICANT' if c['significant'] else 'NOT SIGNIFICANT'} at {ALPHA*100:.0f}%)")
        print(f"    95% CI           : [{c['ci_lo']:+.4f},  {c['ci_hi']:+.4f}]")
        print(f"    R²               : {res['r2']:.3f}   |   Adj-R² : {res['adj_r2']:.3f}")
        if 'rev_growth' in res['coefs']:
            rc = res['coefs']['rev_growth']
            print(f"    Rev-growth coef  : {rc['coef']:+.4f}  "
                  f"(p={rc['pval']:.4f} {sig_star(rc['pval'])})")

    print_model("Model 1 — OPM ~ cost_index (no control)", res1)
    print_model("Model 2 — OPM ~ cost_index + rev_growth", res2)

    if res1 and res2:
        c1 = res1['coefs']['cost_idx']['coef']
        c2 = res2['coefs']['cost_idx']['coef']
        stable = abs(c2 - c1) < abs(c1) * 0.30
        print(f"\n  Coefficient stability check:")
        print(f"    Without control : {c1:+.4f}")
        print(f"    With control    : {c2:+.4f}")
        print(f"    Verdict         : {'STABLE — cost effect appears real' if stable else 'UNSTABLE — volume explains part of the margin move'}")

    # ── 6. Per-firm regression ───────────────────────────────────────────────
    print("\n" + "─" * 72)
    print("  D. PER-FIRM REGRESSION  (firm-specific lag + material weights)")
    print("─" * 72)

    print(f"\n  {'Firm':<28} {'Lag':>4} {'Coef':>8} {'SE':>8} "
          f"{'t-stat':>8} {'p-val':>8} {'Sig':>4} {'R²':>6} {'n':>4}")
    print("  " + "─" * 80)

    firm_results = []
    for f in FIRMS:
        if f not in firm_opm:
            continue
        lag_f = firm_best_lags.get(f, 0)
        xf    = firm_idx[f].shift(lag_f).rename('cost_idx')
        Xf_df = pd.DataFrame(xf)
        if f in firm_rev_gr:
            Xf_df = pd.concat([Xf_df, firm_rev_gr[f].rename('rev_growth')], axis=1)

        res_f = ols_full(firm_opm[f], Xf_df)
        if res_f is None:
            continue

        c = res_f['coefs']['cost_idx']
        row = {
            'firm': f, 'label': FIRM_LABELS[f], 'lag': lag_f,
            'coef': c['coef'], 'se': c['se'],
            'tstat': c['tstat'], 'pval': c['pval'],
            'sig': c['significant'], 'r2': res_f['r2'], 'n': res_f['n'],
            'ci_lo': c['ci_lo'], 'ci_hi': c['ci_hi'],
        }
        firm_results.append(row)
        sig_flag = "Yes" if c['significant'] else "No"
        print(f"  {FIRM_LABELS[f]:<28} {lag_f:>3}Q {c['coef']:>+8.4f} "
              f"{c['se']:>8.4f} {c['tstat']:>+8.3f} {c['pval']:>8.4f} "
              f"{sig_flag:>4} {res_f['r2']:>6.3f} {res_f['n']:>4}")

    print(f"\n  Significance stars: *** p<0.01  ** p<0.05  * p<0.10")
    print(f"  HC1 = heteroskedasticity-robust standard errors (White, df-corrected)")

    # ── 7. Cross-sectional ranking ───────────────────────────────────────────
    print("\n" + "─" * 72)
    print("  E. CROSS-SECTIONAL RANKING  (decision-useful output)")
    print("─" * 72)

    if firm_results:
        by_sensitivity = sorted(firm_results, key=lambda r: r['coef'])
        by_lag         = sorted(firm_results, key=lambda r: r['lag'])

        print("\n  i. By cost SENSITIVITY (most negative coefficient = most exposed):")
        print(f"  {'Rank':<6} {'Firm':<28} {'Coef':>9}  Interpretation")
        print("  " + "─" * 65)
        for rank, r in enumerate(by_sensitivity, 1):
            direction = "↓ OPM contracts" if r['coef'] < 0 else "↑ OPM expands"
            print(f"  #{rank:<5} {r['label']:<28} {r['coef']:>+9.4f}  "
                  f"{direction} {abs(r['coef'])*10:.2f}pp per 10-unit cost rise")

        print("\n  ii. By PASS-THROUGH SPEED (shorter lag = costs hit OPM faster):")
        print(f"  {'Rank':<6} {'Firm':<28} {'Lag':>5}  Interpretation")
        print("  " + "─" * 65)
        for rank, r in enumerate(by_lag, 1):
            speed = "Rapid" if r['lag'] <= 1 else "Moderate" if r['lag'] == 2 else "Slow"
            print(f"  #{rank:<5} {r['label']:<28} {r['lag']:>4}Q  "
                  f"{speed} — costs appear in OPM after ~{r['lag']} quarter(s)")

        print(f"\n  iii. SUMMARY TABLE (for equity analyst use):")
        print("  ┌─────────────────────────────┬─────────┬─────────┬──────────────────────────────┐")
        print("  │ Firm                        │ Opt Lag │ Coef    │ Verdict                      │")
        print("  ├─────────────────────────────┼─────────┼─────────┼──────────────────────────────┤")
        for r in by_sensitivity:
            sig_mark = "*" if r['sig'] else " "
            verdict  = ("High exposure, fast hit" if r['lag'] <= 1 and r['coef'] < -0.05 else
                        "High exposure, slow hit"  if r['lag'] >= 3 and r['coef'] < -0.05 else
                        "Low exposure"             if r['coef'] >= -0.03 else
                        "Moderate exposure")
            print(f"  │ {r['label']:<27} │   {r['lag']}Q    │ {r['coef']:>+7.4f}{sig_mark}│ {verdict:<28} │")
        print("  └─────────────────────────────┴─────────┴─────────┴──────────────────────────────┘")
        print("  * = significant at 10%  (small sample; treat all results directionally)")

    return dict(
        comm=comm, margins=margins, rev=rev, weights=weights,
        firm_idx=firm_idx, sector_idx=sector_idx,
        sector_opm=sector_opm, firm_opm=firm_opm,
        sector_lag_corrs=sector_lag_corrs, best_lag_sector=best_lag_sector,
        firm_lag_corrs_all=firm_lag_corrs_all, firm_best_lags=firm_best_lags,
        res1=res1, res2=res2, firm_results=firm_results,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ═══════════════════════════════════════════════════════════════════════════════

def make_charts(d):
    plt.rcParams.update({
        'font.family': 'DejaVu Sans', 'font.size': 10,
        'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': True, 'grid.alpha': 0.25, 'axes.grid.axis': 'y',
        'figure.facecolor': 'white', 'axes.facecolor': '#FAFAFA',
    })

    qs     = np.arange(len(d['sector_idx']))
    labels = list(d['sector_idx'].index)
    step   = max(1, len(labels) // 8)
    src    = ("Source: investing.com (commodity futures)  |  "
              "screener.in (OPM %)  |  PLACEHOLDER DATA — replace before use")

    # ── Chart 1: Weighted cost index vs Sector OPM ───────────────────────────
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 9), sharex=True,
                                    gridspec_kw={'height_ratios': [1, 1], 'hspace': 0.08})
    ax1.plot(qs, d['sector_idx'].values, '#1F3864', lw=2.2,
             label='Sector weighted cost index (rebased 100)')
    ax1.set_ylabel("Weighted Cost Index\n(Base = 100 at Q1 2018)", fontsize=10)
    ax1.set_title("Weighted Input-Cost Index vs Sector OPM\nIndia Auto-Ancillaries",
                  fontsize=13, fontweight='bold', pad=10)
    ax1.legend(fontsize=9, loc='upper left')

    ax2.plot(qs, d['sector_opm'].values, '#C00000', lw=2.2,
             label='Sector avg OPM %', zorder=5)
    for f in FIRMS:
        if f in d['firm_opm']:
            n = len(d['firm_opm'][f])
            ax2.plot(qs[:n], d['firm_opm'][f].values,
                     FIRM_COLORS[f], lw=1, alpha=0.45, linestyle='--',
                     label=FIRM_LABELS[f])
    ax2.set_ylabel("Operating Profit Margin\n(OPM  %)", fontsize=10)
    ax2.yaxis.set_major_formatter(mtick.PercentFormatter())
    ax2.set_xticks(qs[::step])
    ax2.set_xticklabels([labels[i] for i in range(0, len(labels), step)], rotation=45)
    ax2.legend(fontsize=8, loc='upper left')

    fig.text(0.01, 0.005, src, fontsize=7, color='grey', style='italic')
    plt.tight_layout(rect=[0, 0.03, 1, 1])
    fig.savefig(os.path.join(CHARTS, '01_cost_index_vs_opm.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  ✓ Chart 1 saved: 01_cost_index_vs_opm.png")

    # ── Chart 2: Per-firm lag correlations ───────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left — sector
    lag_range = list(range(MAX_LAG + 1))
    corrs_s   = [d['sector_lag_corrs'].get(l, np.nan) for l in lag_range]
    bar_cols  = ['#C00000' if l == d['best_lag_sector'] else '#ADB9CA' for l in lag_range]
    bars = axes[0].bar([f"{l}Q" for l in lag_range], corrs_s,
                       color=bar_cols, width=0.55, edgecolor='white')
    axes[0].axhline(0, color='#333', lw=0.8)
    for bar, corr in zip(bars, corrs_s):
        if not np.isnan(corr):
            axes[0].text(bar.get_x() + bar.get_width() / 2,
                         corr - 0.05 if corr < 0 else corr + 0.02,
                         f'{corr:+.2f}', ha='center', fontsize=10,
                         color='white' if abs(corr) > 0.3 else 'black', fontweight='bold')
    axes[0].set_title("Sector: OPM vs Cost Index\nCorrelation by Lag",
                      fontweight='bold', fontsize=11)
    axes[0].set_xlabel("Lag (quarters)")
    axes[0].set_ylabel("Pearson Correlation")
    axes[0].set_ylim(-1, 0.6)
    axes[0].annotate(f'Optimal\nlag {d["best_lag_sector"]}Q',
                     xy=(d['best_lag_sector'],
                         d['sector_lag_corrs'][d['best_lag_sector']]),
                     xytext=(d['best_lag_sector'] + 0.5,
                             d['sector_lag_corrs'][d['best_lag_sector']] - 0.18),
                     arrowprops=dict(arrowstyle='->', color='#C00000', lw=1.5),
                     color='#C00000', fontsize=9, fontweight='bold')

    # Right — per firm
    x  = np.arange(MAX_LAG + 1)
    bw = 0.18
    for i, f in enumerate(FIRMS):
        if f not in d['firm_lag_corrs_all']:
            continue
        lc = d['firm_lag_corrs_all'][f]
        corrs_f = [lc.get(l, np.nan) for l in lag_range]
        axes[1].bar(x + (i - 1.5) * bw, corrs_f, bw,
                    label=FIRM_LABELS[f], color=FIRM_COLORS[f], alpha=0.82)
    axes[1].axhline(0, color='#333', lw=0.8)
    axes[1].set_title("Per-Firm Correlation by Lag\n(firm-specific weighted index)",
                      fontweight='bold', fontsize=11)
    axes[1].set_xlabel("Lag (quarters)")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([f'{l}Q' for l in lag_range])
    axes[1].legend(fontsize=8, loc='lower right')
    axes[1].set_ylim(-1, 0.6)
    axes[1].set_ylabel("Pearson Correlation")

    fig.suptitle("Lag Correlation Analysis — OPM vs Weighted Cost Index",
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS, '02_lag_correlations.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  ✓ Chart 2 saved: 02_lag_correlations.png")

    # ── Chart 3: Per-firm OPM time series ────────────────────────────────────
    fig, axes = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    axes_flat = axes.flatten()
    for i, f in enumerate(FIRMS):
        ax = axes_flat[i]
        if f not in d['firm_opm']:
            ax.set_visible(False)
            continue
        opm_arr = d['firm_opm'][f].values
        n       = len(opm_arr)
        ax.plot(qs[:n], opm_arr, FIRM_COLORS[f], lw=2)
        ax.fill_between(qs[:n], opm_arr, alpha=0.12, color=FIRM_COLORS[f])
        ax.set_title(FIRM_LABELS[f], fontweight='bold', fontsize=11)
        ax.set_ylabel("OPM (%)")
        ax.yaxis.set_major_formatter(mtick.PercentFormatter())
        ax.set_xticks(qs[::step])
        ax.set_xticklabels([labels[j] for j in range(0, len(labels), step)],
                           rotation=45, fontsize=8)
    fig.suptitle("Operating Profit Margin (OPM %) by Firm — Quarterly",
                 fontsize=13, fontweight='bold', y=1.01)
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS, '03_per_firm_opm.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  ✓ Chart 3 saved: 03_per_firm_opm.png")

    # ── Chart 4: Metal price trends (rebased to 100) ─────────────────────────
    comm = d['comm']
    fig, ax = plt.subplots(figsize=(14, 6))
    metal_cols = {'steel': '#1F3864', 'aluminium': '#C9A227', 'copper': '#C00000'}
    for metal in METALS:
        if metal in comm.columns:
            idx = rebase_100(comm[metal])
            ax.plot(qs, idx.values, color=metal_cols.get(metal, 'grey'),
                    lw=2, label=metal.capitalize())
    ax.axhline(100, color='grey', lw=0.8, linestyle=':')
    ax.set_ylabel("Price Index (Base = 100 at Q1 2018)")
    ax.set_title("Input-Metal Price Indices — Steel · Aluminium · Copper",
                 fontsize=13, fontweight='bold')
    ax.set_xticks(qs[::step])
    ax.set_xticklabels([labels[i] for i in range(0, len(labels), step)], rotation=45)
    ax.legend(fontsize=10)
    fig.text(0.01, 0.005, src, fontsize=7, color='grey', style='italic')
    plt.tight_layout(rect=[0, 0.04, 1, 1])
    fig.savefig(os.path.join(CHARTS, '04_metal_price_indices.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  ✓ Chart 4 saved: 04_metal_price_indices.png")

    # ── Chart 5: Cross-sectional ranking ─────────────────────────────────────
    fr = d['firm_results']
    if not fr:
        print("  (Skipping Chart 5 — no firm regression results)")
        return

    fig, (ax_l, ax_r) = plt.subplots(1, 2, figsize=(14, 6))

    # Left: cost sensitivity with CI bars
    sorted_s = sorted(fr, key=lambda r: r['coef'])
    y_pos    = np.arange(len(sorted_s))
    coefs    = [r['coef'] for r in sorted_s]
    ci_lo    = [r['ci_lo'] for r in sorted_s]
    ci_hi    = [r['ci_hi'] for r in sorted_s]
    bar_cs   = [FIRM_COLORS[r['firm']] for r in sorted_s]

    ax_l.barh(y_pos, coefs, color=bar_cs, alpha=0.75, height=0.5)
    for j, (lo, hi) in enumerate(zip(ci_lo, ci_hi)):
        ax_l.plot([lo, hi], [j, j], 'k-', lw=2)
        for xv in [lo, hi]:
            ax_l.plot([xv, xv], [j - 0.15, j + 0.15], 'k-', lw=1.5)
    ax_l.axvline(0, color='#333', lw=1)
    ax_l.set_yticks(y_pos)
    ax_l.set_yticklabels([r['label'] for r in sorted_s])
    ax_l.set_xlabel("OPM change (pp) per unit cost-index rise")
    ax_l.set_title("Cost Sensitivity\n(95% CI shown — more negative = more exposed)",
                   fontweight='bold', fontsize=11)

    # Right: pass-through speed
    sorted_l  = sorted(fr, key=lambda r: r['lag'])
    lags_plot = [r['lag'] for r in sorted_l]
    spd_cols  = ['#375623' if l <= 1 else '#BF8F00' if l == 2 else '#ADB9CA'
                 for l in lags_plot]
    ax_r.barh(np.arange(len(sorted_l)), lags_plot,
              color=spd_cols, alpha=0.8, height=0.5)
    ax_r.set_yticks(np.arange(len(sorted_l)))
    ax_r.set_yticklabels([r['label'] for r in sorted_l])
    ax_r.set_xlabel("Optimal lag (quarters)")
    ax_r.set_title("Pass-Through Speed\n(shorter = costs hit OPM faster)",
                   fontweight='bold', fontsize=11)
    ax_r.set_xticks([0, 1, 2, 3, 4])

    patches = [mpatches.Patch(color='#375623', label='Rapid (≤1Q)'),
               mpatches.Patch(color='#BF8F00', label='Moderate (2Q)'),
               mpatches.Patch(color='#ADB9CA', label='Slow (≥3Q)')]
    ax_r.legend(handles=patches, fontsize=8, loc='lower right')

    for ax in [ax_l, ax_r]:
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    fig.suptitle("Cross-Sectional Ranking — Which Firm is Most Exposed?\n"
                 "(coefficients from firm-specific weighted index + firm-optimal lag)",
                 fontsize=12, fontweight='bold')
    plt.tight_layout()
    fig.savefig(os.path.join(CHARTS, '05_cross_sectional_ranking.png'), dpi=150, bbox_inches='tight')
    plt.close()
    print("  ✓ Chart 5 saved: 05_cross_sectional_ranking.png")

    # ── Chart 6: Regression scatter — sector ─────────────────────────────────
    if d['res1']:
        x_cost = d['sector_idx'].shift(d['best_lag_sector'])
        df_sc  = pd.concat([d['sector_opm'], x_cost], axis=1).dropna()
        y_arr  = df_sc.iloc[:, 0].values
        x_arr  = df_sc.iloc[:, 1].values

        fig, ax = plt.subplots(figsize=(9, 7))
        ax.scatter(x_arr, y_arr, color='#2E75B6', alpha=0.75, s=55, zorder=5)

        m_arr = np.column_stack([np.ones(len(x_arr)), x_arr])
        beta, _, _, _ = np.linalg.lstsq(m_arr, y_arr, rcond=None)
        x_line = np.linspace(x_arr.min(), x_arr.max(), 100)
        ax.plot(x_line, beta[0] + beta[1] * x_line,
                '#C00000', lw=2, label=f'OLS  β = {beta[1]:+.4f}')

        r = d['res1']
        c = r['coefs']['cost_idx']
        ax.set_xlabel(f"Weighted Cost Index  (lagged {d['best_lag_sector']}Q)", fontsize=11)
        ax.set_ylabel("Sector OPM  (%)", fontsize=11)
        ax.set_title(
            f"Sector OPM vs Lagged Cost Index\n"
            f"β = {c['coef']:+.4f}   t = {c['tstat']:+.2f}   "
            f"p = {c['pval']:.4f}{sig_star(c['pval'])}   "
            f"R² = {r['r2']:.3f}   n = {r['n']}",
            fontsize=11, fontweight='bold')
        ax.legend(fontsize=10)
        sig_text = ("Statistically significant at 10%  ✓"
                    if c['significant']
                    else f"NOT significant at 10%  —  interpret directionally only")
        color_text = '#375623' if c['significant'] else '#C00000'
        ax.text(0.03, 0.06, sig_text, transform=ax.transAxes,
                fontsize=9, color=color_text, style='italic')
        plt.tight_layout()
        fig.savefig(os.path.join(CHARTS, '06_regression_scatter.png'), dpi=150, bbox_inches='tight')
        plt.close()
        print("  ✓ Chart 6 saved: 06_regression_scatter.png")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    data = run_analysis()
    print("\n" + "─" * 72)
    print("  Generating charts ...")
    print("─" * 72 + "\n")
    make_charts(data)
    print("\n" + "═" * 72)
    print("  Analysis complete.")
    print(f"  Charts saved to: {os.path.abspath(CHARTS)}")
    print("═" * 72 + "\n")
