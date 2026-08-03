# Commodity-to-Margin Sensitivity Study
## India Auto-Ancillaries  |  Steel · Aluminium · Copper  →  OPM
### Q1 2018 – Q4 2024  (28 Quarters)

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

| Company | Primary Product | Material-Cost Profile |
|---|---|---|
| Suprajit Engineering | Cables, wiring harnesses | Copper-heavy + steel |
| Gabriel India | Shock absorbers, suspension | Steel + aluminium |
| Endurance Technologies | Aluminium die-castings, transmission | Aluminium-dominant |
| Sundram Fasteners | Fasteners, forged components | Steel-dominant |

---

## Key Results

Sector-level lag peaks at **3 quarters** — commodity price moves take ~9 months to appear in OPM. Consistent with typical OEM contract renegotiation cycles in India.

| Firm | Optimal Lag | Coefficient | p-value | Verdict |
|---|---|---|---|---|
| Endurance Technologies | 2Q | −0.0837 | 0.002 ✓ | Most exposed — fast hit |
| Suprajit Engineering | 4Q | −0.0706 | 0.094 ✓ | High exposure — slow hit |
| Sundram Fasteners | 3Q | −0.0462 | 0.268 | Lower exposure |
| Gabriel India | 2Q | +0.0213 | 0.503 | Not sensitive |

✓ = significant at 10% level

**Reading this table:** Endurance loses 0.84 pp of OPM for every 10-unit rise in its aluminium-heavy cost index. Sundram Fasteners shows surprising resilience — likely due to fixed-price OEM supply contracts. Gabriel India shows near-zero sensitivity, suggesting better cost pass-through protection in its shock absorber pricing contracts.

---

## Folder Structure

```
commodity-margin-study/
│
├── data/
│   ├── commodity_prices.csv        ← Steel / aluminium / copper quarterly prices
│   ├── quarterly_margins.csv       ← OPM % per firm, per quarter
│   ├── revenue_quarterly.csv       ← Revenue (₹ Cr) per firm, per quarter
│   ├── material_mix_weights.csv    ← Firm-specific RM weights (from annual reports)
│   └── data_entry_guide.md         ← Step-by-step instructions for real data
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

## Data Sources

| Data | Source | Free? | Notes |
|---|---|---|---|
| Steel Rebar Futures | investing.com (Shanghai Rebar) | Yes | Quarterly average of daily close price |
| Aluminium Futures | investing.com (LME Aluminium) | Yes | Quarterly average |
| Copper Futures | investing.com (LME Copper) | Yes | Quarterly average |
| Quarterly OPM % | Moneycontrol — Quarterly Results | Yes | P/L Before Other Inc + Depreciation / Revenue |
| Revenue (₹ Cr) | Moneycontrol — Quarterly Results | Yes | Net Sales row |
| Material weights | Company annual reports (RM breakdown) | Yes | Manual entry once |

> **On OPM vs gross margin:** Strict gross margin requires the raw-material cost line, which is not standardly published in quarterly results. OPM % (Operating Profit Margin) captures the raw-material squeeze and is used consistently throughout this analysis. It equals (Revenue − COGS − Employee costs − Other expenses) / Revenue.

---

## How to Run

**First time setup:**
```bash
pip install pandas numpy matplotlib scipy
```

**Run the analysis:**
```bash
cd notebooks
python analysis.py
```

Charts are saved to `charts/`. Terminal output includes all regression tables and the cross-sectional ranking.

---

## Method

### 1. Firm-specific weighted cost index

Each firm gets its own cost index based on its actual material mix from annual reports:

```
firm_cost_index = w_steel × steel_idx + w_alum × alum_idx + w_copper × copper_idx
```

All three metals are rebased to 100 at the start of the sample before combining. This means Endurance Technologies (aluminium-heavy) gets a different cost trajectory than Sundram Fasteners (steel-heavy) — which is the correct economic representation.

### 2. Lag selection

Pearson correlation is tested between each firm's OPM and its weighted cost index at lags 0, 1, 2, 3, and 4 quarters. The lag with the most negative correlation is selected. The lag is determined by the data, not pre-assumed.

### 3. Regression specification

**Model 1** (baseline):
```
OPM(t) = α + β × cost_index(t − lag) + ε
```

**Model 2** (with volume control):
```
OPM(t) = α + β × cost_index(t − lag) + γ × revenue_growth(t) + ε
```

If β is stable between Model 1 and Model 2, the cost effect is real. If β collapses, volume was doing most of the work — an equally honest and useful finding.

### 4. Statistical reporting

- HC1 heteroskedasticity-robust standard errors (White estimator with df correction)
- t-statistics and p-values reported for every coefficient
- 95% confidence intervals shown on charts and in tables
- Significance assessed at 10% (justified given n ≈ 24–27)
- Stars: *** p<0.01 · ** p<0.05 · * p<0.10

---

## Limitations

- 28 quarters is the minimum for meaningful statistics — treat coefficients as directional
- OPM is a proxy for gross margin (full RM line not published quarterly for all firms)
- Gabriel India pre-2023 data estimated from audited annual totals, not exact quarterly filings
- Material mix weights from annual reports — may not match quarterly variation
- Correlation and regression do not prove causation — macro events affect OPM and metals simultaneously
- Firm-specific contracts, hedging, and inventory management can mute or amplify the effect in ways this model does not capture

---

## Requirements

```
pandas>=1.5
numpy>=1.23
matplotlib>=3.6
scipy>=1.9
```

Install: `pip install pandas numpy matplotlib scipy`
