"""Futures_Main -- CLI entry point.

Runs the full analysis pipeline:
  1. Loads config
  2. Loads data (OI, Volume, Contracts)
  3. Runs all 4 stages + PCR + Max Pain
  4. Exports Excel reports
  5. Optionally sends Telegram alerts
"""

import sys
import os
import argparse

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config import load_config
from src.data_loader import load_participant_oi, load_participant_vol, load_fo_contracts
from src.metrics import (
    compute_oi_snapshot,
    compute_oi_differences,
    compute_contract_positions,
    compute_rolling_averages,
    compute_pcr,
    compute_max_pain,
)
from src.reporter import export_to_excel
from src.alerts import send_telegram_alert, generate_daily_summary


def main(config_path=None):
    """Run the full Futures_Main pipeline."""

    print("=" * 60)
    print("  Futures_Main -- Market Microstructure Analysis")
    print("=" * 60)

    # 1. Load config
    print("\n[1/6] Loading configuration...")
    config = load_config(config_path)
    data_dir = config['data_dir']
    output_dir = config['output_dir']
    rolling_periods = config.get('rolling_periods', [3, 5, 8, 13])
    print(f"  Data dir: {data_dir}")
    print(f"  Output dir: {output_dir}")

    # 2. Load data
    print("\n[2/6] Loading data...")
    df_oi = load_participant_oi(data_dir)
    print(f"  Loaded OI data: {len(df_oi)} rows")

    try:
        df_vol = load_participant_vol(data_dir)
        print(f"  Loaded Volume data: {len(df_vol)} rows")
        has_vol = True
    except FileNotFoundError as e:
        print(f"  [WARN] Volume data not available: {e}")
        df_vol = None
        has_vol = False

    try:
        df_contracts = load_fo_contracts(data_dir)
        print(f"  Loaded Contract data: {len(df_contracts)} rows")
        has_contracts = True
    except FileNotFoundError as e:
        print(f"  [WARN] Contract data not available: {e}")
        df_contracts = None
        has_contracts = False

    # 3. Run stages
    print("\n[3/6] Running Stage 1 -- Participant OI Snapshot...")
    df_snapshot = compute_oi_snapshot(df_oi)
    print(f"  [OK] Snapshot computed ({len(df_snapshot)} rows)")

    if has_vol:
        print("\n[4/6] Running Stage 2 -- OI Differences & Volume Ratios...")
        df_diff = compute_oi_differences(df_oi, df_vol)
        print(f"  [OK] Differences computed ({len(df_diff)} rows)")
    else:
        print("\n[4/6] Skipping Stage 2 (no volume data)")
        df_diff = None

    # PCR
    print("  Computing Put-Call Ratio...")
    df_pcr = compute_pcr(df_oi)
    print(f"  [OK] PCR computed ({len(df_pcr)} rows)")

    reports = {
        'main.xlsx': df_snapshot,
    }

    if df_diff is not None:
        reports['difference.xlsx'] = df_diff

    if has_contracts:
        print("\n[5/6] Running Stage 3 -- Contract Position Classification...")
        df_positions = compute_contract_positions(df_contracts)
        print(f"  [OK] Positions classified ({len(df_positions)} rows)")

        # Max Pain
        print("  Computing Max Pain...")
        df_max_pain = compute_max_pain(df_contracts)
        if not df_max_pain.empty:
            print(f"  [OK] Max Pain computed for {len(df_max_pain)} symbol/expiry combos")
        else:
            print("  [WARN] No Max Pain data (no option instruments found)")

        print("\n  Running Stage 4 -- Rolling Averages...")
        df_rolling = compute_rolling_averages(df_positions, periods=rolling_periods)
        print(f"  [OK] Rolling averages computed (periods: {rolling_periods})")

        reports['Futures_Main.xlsx'] = df_positions
        reports['Rolling.xlsx'] = df_rolling

        if not df_max_pain.empty:
            reports['Max_Pain.xlsx'] = df_max_pain
    else:
        print("\n[5/6] Skipping Stages 3-4 (no contract data)")

    # PCR output
    reports['PCR.xlsx'] = df_pcr

    # 4. Export
    print("\n[6/6] Exporting reports...")
    export_to_excel(reports, output_dir)

    # 5. Alerts
    alerts_config = config.get('alerts', {})
    if alerts_config.get('enabled', False):
        print("\nSending alerts...")
        tg = alerts_config.get('telegram', {})
        bot_token = tg.get('bot_token', '')
        chat_id = tg.get('chat_id', '')
        if bot_token and chat_id:
            summary = generate_daily_summary(df_snapshot)
            send_telegram_alert(summary, bot_token, chat_id)
        else:
            print("  [WARN] Telegram credentials not configured")

    print("\n[DONE] Pipeline complete!")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Futures_Main Analysis Pipeline')
    parser.add_argument('--config', type=str, default=None,
                        help='Path to config.yaml (default: project root)')
    args = parser.parse_args()
    main(config_path=args.config)
