"""Core metrics/analytics module for Futures_Main project.

Contains all computation logic extracted from the original notebook:
  Stage 1 — Participant OI Snapshot
  Stage 2 — Week-on-Week OI Changes with Volume Ratios
  Stage 3 — Contract-Level Position Classification
  Stage 4 — Rolling Averages
  NEW    — Put-Call Ratio (PCR)
  NEW    — Max Pain Calculation
"""

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# Stage 1: Participant OI Snapshot
# ---------------------------------------------------------------------------

def compute_oi_snapshot(df_oi):
    """Compute participant OI snapshot with derived metrics and market views.

    Args:
        df_oi: Raw participant OI DataFrame from data_loader.load_participant_oi()

    Returns:
        pd.DataFrame indexed by (Date, Client Type) with bullish/bearish proxies,
        net positions, market views, and active party identification.
    """
    df2 = df_oi.copy()
    df2.sort_values(by=['Date', 'Client Type'], inplace=True)
    df2.set_index(['Date', 'Client Type'], inplace=True, drop=False)

    # Synthetic bullish/bearish proxies
    df2['Call Long + Put Short Index'] = df2['Option Index Call Long'] + df2['Option Index Put Short']
    df2['Put Long + Call Short Index'] = df2['Option Index Put Long'] + df2['Option Index Call Short']
    df2['Call Long + Put Short Stock'] = df2['Option Stock Call Long'] + df2['Option Stock Put Short']
    df2['Put Long + Call Short Stock'] = df2['Option Stock Put Long'] + df2['Option Stock Call Short']

    # Net positions
    df2['Future Index Net'] = df2['Future Index Long'] - df2['Future Index Short']
    df2['Future Stock Net'] = df2['Future Stock Long'] - df2['Future Stock Short']
    df2['Option Index Net'] = df2['Call Long + Put Short Index'] - df2['Put Long + Call Short Index']
    df2['Option Stock Net'] = df2['Call Long + Put Short Stock'] - df2['Put Long + Call Short Stock']

    # Market views
    df2['Future Index Market View'] = df2['Future Index Long'] > df2['Future Index Short']
    df2['Future Stock Market View'] = df2['Future Stock Long'] > df2['Future Stock Short']
    df2['Option Index Market View'] = df2['Call Long + Put Short Index'] > df2['Put Long + Call Short Index']
    df2['Option Stock Market View'] = df2['Call Long + Put Short Stock'] > df2['Put Long + Call Short Stock']

    # Active Party identification
    df2['FUTIDX Active Party1'] = df2['Future Index Long'] + df2['Future Index Short']
    df2['FUTSTK Active Party1'] = df2['Future Stock Long'] + df2['Future Stock Short']
    df2['OPTIDX Active Party1'] = (df2['Option Index Call Long'] + df2['Option Index Put Long'] +
                                    df2['Option Index Call Short'] + df2['Option Index Put Short'])
    df2['OPTSTK Active Party1'] = (df2['Option Stock Call Long'] + df2['Option Stock Put Long'] +
                                    df2['Option Stock Call Short'] + df2['Option Stock Put Short'])

    df2['FUTIDX Active Party2'] = df2.groupby(level=0)['FUTIDX Active Party1'].transform('max')
    df2['FUTSTK Active Party2'] = df2.groupby(level=0)['FUTSTK Active Party1'].transform('max')
    df2['OPTIDX Active Party2'] = df2.groupby(level=0)['OPTIDX Active Party1'].transform('max')
    df2['OPTSTK Active Party2'] = df2.groupby(level=0)['OPTSTK Active Party1'].transform('max')

    # Map boolean market views to labels
    mv_cols = ['Future Index Market View', 'Future Stock Market View',
               'Option Index Market View', 'Option Stock Market View']
    for col in mv_cols:
        df2[col] = df2[col].map({True: 'Bullish', False: 'Bearish'})

    # Identify active party
    df2['FUTIDX Active Party'] = df2[df2['FUTIDX Active Party1'] == df2['FUTIDX Active Party2']]['Client Type']
    df2['FUTSTK Active Party'] = df2[df2['FUTSTK Active Party1'] == df2['FUTSTK Active Party2']]['Client Type']
    df2['OPTIDX Active Party'] = df2[df2['OPTIDX Active Party1'] == df2['OPTIDX Active Party2']]['Client Type']
    df2['OPTSTK Active Party'] = df2[df2['OPTSTK Active Party1'] == df2['OPTSTK Active Party2']]['Client Type']

    # Cleanup helper columns
    drop_cols = ['FUTIDX Active Party1', 'FUTIDX Active Party2',
                 'FUTSTK Active Party1', 'FUTSTK Active Party2',
                 'OPTIDX Active Party1', 'OPTIDX Active Party2',
                 'OPTSTK Active Party1', 'OPTSTK Active Party2']
    df2.drop(columns=drop_cols, inplace=True)

    df2.set_index(['Date', 'Client Type'], inplace=True, drop=True)
    df2.sort_values(by=['Date', 'Client Type'], inplace=True)

    return df2


# ---------------------------------------------------------------------------
# Stage 2: OI Differences / Week-on-Week Changes
# ---------------------------------------------------------------------------

def compute_oi_differences(df_oi, df_vol):
    """Compute period-on-period OI changes and volume ratios.

    Args:
        df_oi: Raw participant OI DataFrame (NOT the snapshot).
        df_vol: Raw participant volume DataFrame.

    Returns:
        pd.DataFrame indexed by (Date, Client Type) with OI diffs, market views,
        and volume ratios.
    """
    df = df_oi.copy()
    df.sort_values(by=['Date', 'Client Type'], inplace=True)
    df.set_index(['Date', 'Client Type'], inplace=True, drop=True)

    # Validate 4 rows per date
    rows_per_date = df.groupby(level=0).size()
    assert rows_per_date.eq(4).all(), \
        f"Expected 4 rows per date (one per client type). Got:\n{rows_per_date[rows_per_date != 4]}"

    difference = df.diff(periods=4)

    # Synthetic proxies on the diff
    difference['Call Long + Put Short Index'] = difference['Option Index Call Long'] + difference['Option Index Put Short']
    difference['Put Long + Call Short Index'] = difference['Option Index Put Long'] + difference['Option Index Call Short']
    difference['Call Long + Put Short Stock'] = difference['Option Stock Call Long'] + difference['Option Stock Put Short']
    difference['Put Long + Call Short Stock'] = difference['Option Stock Put Long'] + difference['Option Stock Call Short']

    difference['Future Index Net'] = difference['Future Index Long'] - difference['Future Index Short']
    difference['Future Stock Net'] = difference['Future Stock Long'] - difference['Future Stock Short']
    difference['Option Index Net'] = difference['Call Long + Put Short Index'] - difference['Put Long + Call Short Index']
    difference['Option Stock Net'] = difference['Call Long + Put Short Stock'] - difference['Put Long + Call Short Stock']

    difference['Future Index Market View'] = difference['Future Index Long'] > difference['Future Index Short']
    difference['Future Stock Market View'] = difference['Future Stock Long'] > difference['Future Stock Short']
    difference['Option Index Market View'] = difference['Call Long + Put Short Index'] > difference['Put Long + Call Short Index']
    difference['Option Stock Market View'] = difference['Call Long + Put Short Stock'] > difference['Put Long + Call Short Stock']

    mv_cols = ['Future Index Market View', 'Future Stock Market View',
               'Option Index Market View', 'Option Stock Market View']
    for col in mv_cols:
        difference[col] = difference[col].map({True: 'Bullish', False: 'Bearish'})

    # Merge volume data
    dfv = df_vol.copy()
    if 'Total Long Contracts' in dfv.columns:
        dfv.drop(columns=['Total Long Contracts', 'Total Short Contracts'], inplace=True, errors='ignore')
    dfv.set_index(['Date', 'Client Type'], inplace=True, drop=True)
    dfv.sort_values(by=['Date', 'Client Type'], inplace=True)

    vol_rename = {
        "Future Index Long": "Vol Future Index Long",
        "Future Index Short": "Vol Future Index Short",
        "Future Stock Long": "Vol Future Stock Long",
        "Future Stock Short": "Vol Future Stock Short",
        "Option Index Call Long": "Vol Option Index Call Long",
        "Option Index Put Long": "Vol Option Index Put Long",
        "Option Index Call Short": "Vol Option Index Call Short",
        "Option Index Put Short": "Vol Option Index Put Short",
        "Option Stock Call Long": "Vol Option Stock Call Long",
        "Option Stock Put Long": "Vol Option Stock Put Long",
        "Option Stock Call Short": "Vol Option Stock Call Short",
        "Option Stock Put Short": "Vol Option Stock Put Short",
    }
    dfv.rename(columns=vol_rename, inplace=True)
    difference = pd.merge(difference, dfv, how='left', left_index=True, right_index=True)

    # Volume Ratios
    vr_pairs = [
        ('VR FUTIDX Long', 'Future Index Long', 'Vol Future Index Long'),
        ('VR FUTINDX Short', 'Future Index Short', 'Vol Future Index Short'),
        ('VR FUTSTK Long', 'Future Stock Long', 'Vol Future Stock Long'),
        ('VR FUTSTK Short', 'Future Stock Short', 'Vol Future Stock Short'),
        ('VR OPTIDX CE Long', 'Option Index Call Long', 'Vol Option Index Call Long'),
        ('VR OPTIDX PE Long', 'Option Index Put Long', 'Vol Option Index Put Long'),
        ('VR OPTIDX CE Short', 'Option Index Call Short', 'Vol Option Index Call Short'),
        ('VR OPTIDX PE Short', 'Option Index Put Short', 'Vol Option Index Put Short'),
        ('VR OPTSTK CE Long', 'Option Stock Call Long', 'Vol Option Stock Call Long'),
        ('VR OPTSTK PE Long', 'Option Stock Put Long', 'Vol Option Stock Put Long'),
        ('VR OPTSTK CE Short', 'Option Stock Call Short', 'Vol Option Stock Call Short'),
        ('VR OPTSTK PE Short', 'Option Stock Put Short', 'Vol Option Stock Put Short'),
    ]
    for vr_col, oi_col, vol_col in vr_pairs:
        difference[vr_col] = difference[oi_col].div(
            difference[vol_col].replace(0, np.nan))

    return difference


# ---------------------------------------------------------------------------
# Stage 3: Contract-Level Position Classification
# ---------------------------------------------------------------------------

def compute_contract_positions(df_contracts):
    """Classify contract positions as Long/Short/Short Covering/Long Unwinding.

    Args:
        df_contracts: Contract-level F&O DataFrame from data_loader.load_fo_contracts()

    Returns:
        pd.DataFrame with position classification and Big Position flag.
    """
    df = df_contracts.copy()

    # Ensure required columns exist
    required = ['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'TIMESTAMP',
                'CLOSE', 'OPEN_INT', 'CHG_IN_OI', 'CONTRACTS']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in contract data: {missing}")

    df.sort_values(by=['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'TIMESTAMP'], inplace=True)

    # Price change
    df['PRICE_CHANGE'] = df.groupby(['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT'])['CLOSE'].diff()

    # Position classification
    conditions = [
        (df['PRICE_CHANGE'] > 0) & (df['CHG_IN_OI'] > 0),   # Long
        (df['PRICE_CHANGE'] < 0) & (df['CHG_IN_OI'] > 0),   # Short
        (df['PRICE_CHANGE'] > 0) & (df['CHG_IN_OI'] < 0),   # Short Covering
        (df['PRICE_CHANGE'] < 0) & (df['CHG_IN_OI'] < 0),   # Long Unwinding
    ]
    choices = ['Long', 'Short', 'Short Covering', 'Long Unwinding']
    df['Position'] = np.select(conditions, choices, default='Neutral')

    # Big Position flag: average trade size > historical mean
    if 'CONTRACTS' in df.columns and 'OPEN_INT' in df.columns:
        # Average trade size = CONTRACTS (volume proxy)
        df['Avg Trade Size'] = df['CONTRACTS']
        mean_trade_size = df['Avg Trade Size'].mean()
        df['Big Position'] = df['Avg Trade Size'] > mean_trade_size
    else:
        df['Big Position'] = False

    return df


# ---------------------------------------------------------------------------
# Stage 4: Rolling Averages
# ---------------------------------------------------------------------------

def compute_rolling_averages(df_contracts, periods=None):
    """Compute rolling averages over Fibonacci periods for contracts.

    Args:
        df_contracts: Contract-level DataFrame (output of compute_contract_positions
                      or raw from load_fo_contracts).
        periods: List of rolling window sizes. Defaults to [3, 5, 8, 13].

    Returns:
        pd.DataFrame with rolling average columns appended.
    """
    if periods is None:
        periods = [3, 5, 8, 13]

    df = df_contracts.copy()
    df.sort_values(by=['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT', 'TIMESTAMP'], inplace=True)

    group_cols = ['INSTRUMENT', 'SYMBOL', 'EXPIRY_DT']
    value_cols = ['CLOSE', 'CONTRACTS', 'OPEN_INT']
    existing_value_cols = [c for c in value_cols if c in df.columns]

    for period in periods:
        for col in existing_value_cols:
            new_col = f'{col}_RA{period}'
            df[new_col] = df.groupby(group_cols)[col].transform(
                lambda x: x.rolling(window=period, min_periods=1).mean()
            )

    return df


# ---------------------------------------------------------------------------
# NEW: Put-Call Ratio (PCR)
# ---------------------------------------------------------------------------

def compute_pcr(df_oi):
    """Compute Put-Call Ratio based on OI data.

    Calculates PCR for both Index Options and Stock Options.

    Args:
        df_oi: Raw participant OI DataFrame.

    Returns:
        pd.DataFrame indexed by Date with PCR columns.
    """
    df = df_oi.copy()

    # Aggregate across all participant types per date
    daily = df.groupby('Date').sum(numeric_only=True)

    # Index Options PCR (OI-based)
    daily['PCR Index OI'] = (
        (daily['Option Index Put Long'] + daily['Option Index Put Short']) /
        (daily['Option Index Call Long'] + daily['Option Index Call Short']).replace(0, np.nan)
    )

    # Stock Options PCR (OI-based)
    daily['PCR Stock OI'] = (
        (daily['Option Stock Put Long'] + daily['Option Stock Put Short']) /
        (daily['Option Stock Call Long'] + daily['Option Stock Call Short']).replace(0, np.nan)
    )

    # Combined PCR
    total_puts = (daily['Option Index Put Long'] + daily['Option Index Put Short'] +
                  daily['Option Stock Put Long'] + daily['Option Stock Put Short'])
    total_calls = (daily['Option Index Call Long'] + daily['Option Index Call Short'] +
                   daily['Option Stock Call Long'] + daily['Option Stock Call Short'])
    daily['PCR Combined'] = total_puts / total_calls.replace(0, np.nan)

    return daily[['PCR Index OI', 'PCR Stock OI', 'PCR Combined']]


# ---------------------------------------------------------------------------
# NEW: Max Pain Calculation
# ---------------------------------------------------------------------------

def compute_max_pain(df_contracts):
    """Compute Max Pain for each expiry in the contract data.

    Max Pain is the strike price at which the total value of outstanding
    options (calls + puts) expires worthless for the maximum number of
    option holders—i.e., where option writers (sellers) have minimum loss.

    Args:
        df_contracts: Contract-level DataFrame with INSTRUMENT, SYMBOL,
                      EXPIRY_DT, STRIKE_PR, OPTION_TYP, OPEN_INT columns.

    Returns:
        pd.DataFrame with SYMBOL, EXPIRY_DT, and Max_Pain columns.
    """
    df = df_contracts.copy()

    # Filter to options only
    opt_instruments = ['OPTIDX', 'OPTSTK']
    df_opt = df[df['INSTRUMENT'].isin(opt_instruments)].copy()

    if df_opt.empty or 'STRIKE_PR' not in df_opt.columns or 'OPTION_TYP' not in df_opt.columns:
        return pd.DataFrame(columns=['SYMBOL', 'EXPIRY_DT', 'Max_Pain'])

    # Get latest date per symbol/expiry
    latest = df_opt.groupby(['SYMBOL', 'EXPIRY_DT'])['TIMESTAMP'].max().reset_index()
    df_opt = df_opt.merge(latest, on=['SYMBOL', 'EXPIRY_DT', 'TIMESTAMP'], how='inner')

    results = []
    for (symbol, expiry), group in df_opt.groupby(['SYMBOL', 'EXPIRY_DT']):
        strikes = group['STRIKE_PR'].unique()
        min_pain = float('inf')
        max_pain_strike = None

        for strike in strikes:
            total_pain = 0
            for _, row in group.iterrows():
                oi = row.get('OPEN_INT', 0)
                if row['OPTION_TYP'] == 'CE':
                    # Call pain at this strike
                    intrinsic = max(0, strike - row['STRIKE_PR'])
                    total_pain += intrinsic * oi
                elif row['OPTION_TYP'] == 'PE':
                    # Put pain at this strike
                    intrinsic = max(0, row['STRIKE_PR'] - strike)
                    total_pain += intrinsic * oi

            if total_pain < min_pain:
                min_pain = total_pain
                max_pain_strike = strike

        if max_pain_strike is not None:
            results.append({
                'SYMBOL': symbol,
                'EXPIRY_DT': expiry,
                'Max_Pain': max_pain_strike
            })

    return pd.DataFrame(results)
