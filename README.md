# Commodity-to-Margin Sensitivity Study
## India Auto-Ancillaries  |  Steel · Aluminium · Copper  →  OPM

---

## Objective

Auto-parts makers buy steel, aluminium, and copper in large quantities.
When input prices rise, their costs increase immediately — but selling prices
to carmakers reset only periodically. This creates a **margin squeeze with a lag**.

This study measures:
1. **How strongly** input-cost moves correlate with operating profit margin (OPM) changes.
2. **Which lag** (0–4 quarters) produces the strongest correlation — determined by data, not assumed.
3. **The size of the effect** — with t-statistics, p-values, and 95% confidence intervals.
4. **Firm-specific variation** — which company is most exposed, and which passes costs through fastest.
5. **Whether volume or cost** is driving the margin move (revenue growth control variable).

---

## Companies

| Company | Primary product | Material-cost profile |
|---|---|---|
| Suprajit Engineering | Cables, wiring harnesses | Copper-heavy + steel |
| Gabriel India | Shock absorbers, suspension | Steel + aluminium |
| Endurance Technologies | Aluminium die-castings, transmission | Aluminium-dominant |
| Sundram Fasteners | Fasteners, forged components | Steel-dominant |

---

## Folder structure

```
commodity-margin-study/
│
├── data/
│   ├── data_entry_guide.md         ← Step-by-step instructions for real data
│   ├── commodity_prices.csv        ← Steel / aluminium / copper quarterly prices
│   ├── quarterly_margins.csv       ← OPM % per firm, per quarter
│   ├── revenue_quarterly.csv       ← Revenue (₹ Cr) per firm, per quarter
│   └── material_mix_weights.csv    ← Firm-specific RM weights (from annual reports)
│
├── notebooks/
│   └── analysis.py                 ← Complete analysis — run this
│
├── charts/                         ← Auto-generated when analysis.py runs
│   ├── 01_cost_index_vs_opm.png
│   ├── 02_lag_correlations.png
│   ├── 03_per_firm_opm.png
│   ├── 04_metal_price_indices.png
│   ├── 05_cross_sectional_ranking.png
│   └── 06_regression_scatter.png
│
├── requirements.txt
└── README.md
```

---

## Data sources

| Data | Source | Free? | Notes |
|---|---|---|---|
| Steel Rebar Futures | investing.com (Shanghai Rebar) | Yes | Quarterly average of daily close price |
| Aluminium Futures | investing.com (LME Aluminium) | Yes | Quarterly average |
| Copper Futures | investing.com (LME Copper) | Yes | Quarterly average |
| Quarterly OPM % | screener.in → Quarterly Results | Yes | OPM % row, consolidated |
| Revenue (₹ Cr) | screener.in → Quarterly Results | Yes | Sales row, consolidated |
| Material weights | Company annual reports (RM breakdown) | Yes | Manual entry once |

> **On OPM vs gross margin:** Strict gross margin requires the raw-material cost line,
> which is not standardly published in quarterly results. OPM % (Operating Profit Margin)
> is consistently available on screener.in for all four firms, captures the raw-material
> squeeze, and is used **consistently as OPM throughout this analysis**.
> It equals (Revenue − COGS − Employee costs − Other expenses) / Revenue.

---

## How to run

**First time setup:**
```bash
pip install pandas numpy matplotlib scipy
```

**Run the analysis:**
```bash
cd notebooks
python analysis.py
```

Charts are saved to `charts/`. Terminal output includes all regression tables.


Follow `data/data_entry_guide.md` — approximately 2–3 hours of manual entry.

---

## Method

### 1. Firm-specific weighted cost index
Each firm gets its own cost index based on its **actual material mix** (from annual reports):

```
firm_cost_index = w_steel × steel_idx + w_alum × alum_idx + w_copper × copper_idx
```

All three metals are rebased to 100 at the start of the sample before combining.
This means Endurance Technologies (aluminium-heavy) gets a different cost trajectory
than Sundram Fasteners (steel-heavy) — which is the correct economic representation.

### 2. Lag selection
Pearson correlation is tested between each firm's OPM and its weighted cost index at lags
0, 1, 2, 3, and 4 quarters. The lag with the **most negative correlation is selected**.
The lag is **determined by the data**, not pre-assumed.

### 3. Regression specification

**Model 1** (baseline):
```
OPM(t) = α + β × cost_index(t − lag) + ε
```

**Model 2** (with volume control):
```
OPM(t) = α + β × cost_index(t − lag) + γ × revenue_growth(t) + ε
```

If the cost coefficient β is stable between Model 1 and Model 2, the cost effect is real.
If β collapses, volume was doing most of the work — an equally honest and useful finding.

### 4. Statistical reporting
- HC1 heteroskedasticity-robust standard errors (White estimator with df correction)
- t-statistics and p-values reported for every coefficient
- 95% confidence intervals shown on charts and in tables
- Significance assessed at 10% (justified given n ≈ 24–27)
- Stars: *** p<0.01 · ** p<0.05 · * p<0.10

### 5. Cross-sectional output
Two rankings:
- **By cost sensitivity** (coefficient magnitude) — which firm's OPM contracts most per unit cost rise
- **By pass-through speed** (optimal lag) — which firm feels the hit fastest

---

## Key output: Summary ranking table

The terminal output includes a decision-useful table like this
(numbers below are from PLACEHOLDER data — replace before use):

```

| Firm | Opt Lag | Coef | Verdict |
|---|---|---|---|
| Endurance Technologies | 2Q | −0.0837* | Most exposed — fast hit |
| Suprajit Engineering | 4Q | −0.0706* | High exposure — slow hit |
| Sundram Fasteners | 3Q | −0.0462 | Lower exposure |
| Gabriel India | 2Q | +0.0213 | Not sensitive |

* significant at 10%

```

This is the **actionable conclusion** for an equity analyst:
when steel/aluminium/copper prices spike, which firm to watch first, and why.

---

## Limitations

- 28 quarters is the minimum for meaningful statistics — 16+ required to draw any conclusions
- OPM is a proxy for gross margin (full RM line not published quarterly)
- Material mix weights estimated from annual reports — may not match quarterly variation
- Correlation and regression do not prove causation — macro events affect OPM and metals simultaneously
- Firm-specific contracts, hedging, and inventory management can mute or amplify the effect in ways this model does not capture
- p-values for small samples require caution — treat coefficients as directional, not precise

---

## Requirements

```
pandas>=1.5
numpy>=1.23
matplotlib>=3.6
scipy>=1.9
```

Install: `pip install pandas numpy matplotlib scipy`

---

*Data: investing.com (commodity futures) + screener.in (quarterly financials).
All placeholder data must be replaced with real values before drawing conclusions.*
