# Futures_Main

A market microstructure analysis tool for the Indian derivatives market (NSE). Processes publicly available NSE F&O participant-wise data to track institutional vs retail sentiment, classify market positioning, and generate actionable Excel reports.

## Data Sources

| File Pattern | Content |
|---|---|
| `data/fao_participant_oi_*.csv` | Open Interest by participant type & date |
| `data/fao_participant_vol*.csv` | Volume by participant type & date |
| `data/fo*.zip` | Contract-level daily F&O data (price, OI, volume per symbol/expiry) |

**Participant types:** `Client` (retail), `DII` (Domestic Institutional), `FII` (Foreign Institutional), `Pro` (Proprietary/broker)

## Analysis Pipeline

### Stage 1 — Participant OI Snapshot → `main.xlsx`
- Computes synthetic bullish/bearish proxies: `Call Long + Put Short` vs `Put Long + Call Short`
- Derives net positions for Futures and Options (Index & Stock)
- Labels each participant's market view as **Bullish** or **Bearish**
- Identifies the **Active Party** (participant with largest OI) per instrument per day

### Stage 2 — Week-on-Week Changes → `difference.xlsx`
- Calculates period-on-period OI changes per participant type
- Computes **Volume Ratios (VR)** = OI change / Volume — a VR > 1 signals heavy OI buildup relative to trading activity

### Stage 3 — Contract-Level F&O Analysis → `Futures_Main.xlsx`
Classifies each contract (instrument + symbol + expiry) by position type:

| Position | Price | OI | Meaning |
|---|---|---|---|
| **Long** | ↑ | ↑ | Fresh long positions being built |
| **Short** | ↓ | ↑ | Fresh short positions being built |
| **Short Covering** | ↑ | ↓ | Shorts exiting |
| **Long Unwinding** | ↓ | ↓ | Longs exiting |

Also flags **Big Position** when average trade size exceeds the historical mean — a signal of institutional-sized activity.

### Stage 4 — Rolling Averages → `Rolling.xlsx`
- Computes rolling averages over Fibonacci periods: **3, 5, 8, 13 days**
- Covers Price, Volume, and Open Interest per contract
- Merges onto current-day positions for multi-timeframe context

## Outputs

| File | Description |
|---|---|
| `main.xlsx` | Participant OI snapshot with derived metrics and market views |
| `difference.xlsx` | Period-on-period OI changes with volume ratios |
| `Futures_Main.xlsx` | Contract-level analysis with position classification |
| `Rolling.xlsx` | Current positions enriched with 3/5/8/13-day rolling averages |

## Usage

Open and run `Futures_Main.ipynb` in Jupyter. All four outputs are regenerated on each run.

## Key Questions Answered

1. **Who is bullish/bearish?** — FII, DII, retail, or prop desks
2. **Are positions building or unwinding?** — Long vs Short Covering vs Long Unwinding etc.
3. **Is there institutional-sized activity?** — Big Position flag
4. **How do current positions compare to recent trend?** — 3/5/8/13-day rolling averages
