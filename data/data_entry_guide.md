# Data Entry Guide
## Commodity-to-Margin Sensitivity Study

Follow these steps to replace the placeholder data with real numbers.
This is a one-time effort — approximately 2–3 hours.

---

## Overview of files to fill

| File | Source | Time needed |
|---|---|---|
| `commodity_prices.csv` | investing.com | 30 min |
| `quarterly_margins.csv` | screener.in | 60 min |
| `revenue_quarterly.csv` | screener.in | 60 min |
| `material_mix_weights.csv` | Annual reports | 30 min (verify only) |

---

## QUARTER LABEL FORMAT

All three CSV files use the same quarter format: `YYYY-QN`

| Label | Calendar period | screener.in shows |
|---|---|---|
| 2018-Q1 | Jan – Mar 2018 | "Mar 2018" |
| 2018-Q2 | Apr – Jun 2018 | "Jun 2018" |
| 2018-Q3 | Jul – Sep 2018 | "Sep 2018" |
| 2018-Q4 | Oct – Dec 2018 | "Dec 2018" |
| 2019-Q1 | Jan – Mar 2019 | "Mar 2019" |

screener.in labels quarters by their LAST MONTH. So "Mar 2018" = Q1 2018 = 2018-Q1 in our files.

---

## Step 1 — Commodity Prices  (`commodity_prices.csv`)

**Source: investing.com (free, no login needed for historical data)**

### Steel Rebar Futures
1. Go to: `investing.com`
2. In the search box, type: **Steel Rebar Futures**
3. Click on the result (usually shows Shanghai Rebar Steel Futures — SRB)
4. Click the **Historical Data** tab
5. Set date range: **01/01/2018 to 31/12/2024**
6. Click **Apply**
7. Click **Download Data** (top right of the table) → CSV file downloads
8. Open the CSV. You will see columns: Date, Price, Open, High, Low, Change%, Vol
9. You need the quarterly AVERAGE of the **Price** (close price) column
10. Average all daily prices within each Jan-Mar period → that is Q1 2018
    Average all daily prices within Apr-Jun → Q2 2018, and so on
11. Enter the average price (USD/ton) for each quarter in `commodity_prices.csv` column `steel`

### Aluminium Futures (LME)
- Search: **Aluminium Futures** on investing.com
- Click on LME Aluminium (ticker: AHK... or similar)
- Repeat steps 4–11 above for column `aluminium`

### Copper Futures (LME)
- Search: **Copper Futures** on investing.com
- Click on LME Copper
- Repeat steps 4–11 above for column `copper`

**The analysis script automatically indexes all three to 100 at Q1 2018. You can enter raw USD/ton prices.**

---

## Step 2 — Operating Profit Margins  (`quarterly_margins.csv`)

**Source: screener.in (free, creates a free account if asked)**

For EACH of the four companies, follow these steps:

### Company 1: Suprajit Engineering
1. Go to: `screener.in`
2. In the search box, type: **Suprajit Engineering**
3. Click on the company name in search results
4. On the company page, click the **Quarterly** tab (below the financial tables)
5. Look for the row labelled **OPM %** (Operating Profit Margin %)
6. Copy the value for each quarter going back to **Mar 2018**
   - screener.in shows newest first — scroll right or down for older data
7. Enter into `quarterly_margins.csv` column `suprajit`
   - screener.in "Mar 2018" → row `2018-Q1`
   - screener.in "Jun 2018" → row `2018-Q2`, etc.

### Company 2: Gabriel India
- Search: **Gabriel India** on screener.in
- Repeat the same steps → enter in column `gabriel`

### Company 3: Endurance Technologies
- Search: **Endurance Technologies** on screener.in
- Enter in column `endurance`

### Company 4: Sundram Fasteners
- Search: **Sundram Fasteners** on screener.in
- Enter in column `sundram`

**Important:** If a company's quarterly history only goes back to, say, mid-2019 on screener.in,
leave the earlier rows blank. The analysis handles missing data automatically.

---

## Step 3 — Revenue  (`revenue_quarterly.csv`)

**Source: screener.in (same pages as Step 2)**

On the same Quarterly page for each company:
- Look for the row labelled **Sales** or **Revenue** (₹ Crores)
- Copy the value for each quarter going back to Mar 2018
- Enter in `revenue_quarterly.csv` in the column for that firm

Revenue is used as a **control variable** — to separate "margins fell because costs rose"
from "margins fell because sales volume dropped." Both things matter.

---

## Step 4 — Material Mix Weights  (`material_mix_weights.csv`)

**Source: Annual Reports (already partially filled — verify only)**

The weights in this file are ESTIMATES based on public disclosures.
To verify or update:

For each company:
1. Search: "[Company name] Annual Report 2024 PDF"
2. Open the report and search for "Raw Material" or "Cost of Materials Consumed"
3. Look for a breakdown showing: Steel / Aluminium / Copper / Other as % of total RM cost
4. Update the weights in `material_mix_weights.csv`

The weights do NOT need to sum to 1.0 — the code normalises them.

Current estimates (verify):
- **Suprajit**: copper-heavy (wiring harnesses) + steel (cables)
- **Gabriel**: steel tubes + aluminium die-castings
- **Endurance**: aluminium-dominant (die castings, gear boxes)
- **Sundram**: steel-dominant (forged and machined fasteners)

---

## Step 5 — Re-run the analysis

After filling all files, open a terminal in the `notebooks/` folder and run:

```
python analysis.py
```

The script will:
- Print t-statistics, p-values, and confidence intervals for all regressions
- Determine the optimal lag from your real data (not pre-assumed)
- Save 6 updated charts to the `charts/` folder
- Print the cross-sectional ranking table

---

## Common mistakes to avoid

| Mistake | How to avoid |
|---|---|
| Entering OPM as a decimal (e.g., 0.14) | Enter as percentage (e.g., 14.2) |
| Mixing up quarters (Mar 2018 = Q1, not Q4) | Check the table at the top of this guide |
| Leaving a row blank for all four firms | At least one firm must have data in that quarter |
| Entering revenue in rupees not crores | screener.in already shows in Crores — no conversion needed |
| Using OPM% from standalone instead of consolidated | Use consolidated quarterly results |

---

## If screener.in does not show data back to 2018

Some companies may only show 8–12 quarters on the free tier.
Options:
- Create a free account on screener.in — this often unlocks more history
- Check the Quarterly Results section on the company's own investor relations page
- Use the NSE India website → Quarterly Results PDFs → manually read OPM for missing quarters

Minimum useful history: 16 quarters (4 years). 28 quarters is ideal.
