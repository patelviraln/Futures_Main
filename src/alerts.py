"""Alerts module — sends notifications after pipeline runs.

Currently supports Telegram alerts via Bot API.
"""

import requests


def send_telegram_alert(message, bot_token, chat_id):
    """Send a text message via Telegram Bot API.

    Args:
        message: The alert text.
        bot_token: Telegram bot token from @BotFather.
        chat_id: Target chat/group ID.

    Returns:
        True if successful, False otherwise.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"  [WARN] Failed to send Telegram alert: {e}")
        return False


def generate_daily_summary(df_snapshot, df_differences=None):
    """Generate a human-readable daily summary of key signals.

    Args:
        df_snapshot: OI snapshot DataFrame (output of compute_oi_snapshot).
        df_differences: OI differences DataFrame (optional).

    Returns:
        str summary text.
    """
    lines = ["📊 *Futures Main — Daily Summary*\n"]

    # Get latest date
    if hasattr(df_snapshot.index, 'get_level_values'):
        dates = df_snapshot.index.get_level_values('Date')
    else:
        dates = df_snapshot.get('Date', [])

    if len(dates) > 0:
        max_date = dates.max()
        lines.append(f"Date: {max_date.strftime('%d-%b-%Y')}\n")

        latest = df_snapshot[df_snapshot.index.get_level_values('Date') == max_date]

        # Market views
        mv_cols = ['Future Index Market View', 'Future Stock Market View',
                   'Option Index Market View', 'Option Stock Market View']

        for _, row in latest.iterrows():
            client_type = row.get('Client Type', row.name[1] if isinstance(row.name, tuple) else 'Unknown')
            views = []
            for col in mv_cols:
                if col in latest.columns:
                    val = row.get(col, '')
                    instrument = col.replace(' Market View', '')
                    emoji = '🟢' if val == 'Bullish' else '🔴'
                    views.append(f"  {emoji} {instrument}: {val}")
            if views:
                lines.append(f"\n*{client_type}*")
                lines.extend(views)

    return '\n'.join(lines)
