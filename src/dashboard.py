"""Futures_Main — Streamlit Interactive Dashboard.

Launch with:  streamlit run src/dashboard.py
"""

import sys
import os

# Ensure project root is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

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


# ── Helpers ──────────────────────────────────────────────────────────────────

def color_market_view(val):
    """Styler function to color Bullish green and Bearish red."""
    if val == 'Bullish':
        return 'background-color: #c6efce; color: #006100'
    elif val == 'Bearish':
        return 'background-color: #ffc7ce; color: #9c0006'
    return ''


@st.cache_data(show_spinner=False)
def load_all_data(config):
    """Load and compute all datasets (cached)."""
    data_dir = config['data_dir']
    rolling_periods = config.get('rolling_periods', [3, 5, 8, 13])

    df_oi = load_participant_oi(data_dir)
    df_vol = load_participant_vol(data_dir)

    df_snapshot = compute_oi_snapshot(df_oi)
    df_diff = compute_oi_differences(df_oi, df_vol)
    df_pcr = compute_pcr(df_oi)

    try:
        df_contracts = load_fo_contracts(data_dir)
        df_positions = compute_contract_positions(df_contracts)
        df_rolling = compute_rolling_averages(df_positions, periods=rolling_periods)
        df_max_pain = compute_max_pain(df_contracts)
    except FileNotFoundError:
        df_positions = None
        df_rolling = None
        df_max_pain = None

    return {
        'snapshot': df_snapshot,
        'diff': df_diff,
        'pcr': df_pcr,
        'positions': df_positions,
        'rolling': df_rolling,
        'max_pain': df_max_pain,
    }


# ── Main App ─────────────────────────────────────────────────────────────────

def main():
    config = load_config()

    st.set_page_config(
        page_title=config.get('dashboard', {}).get('page_title', 'Futures Main'),
        page_icon=config.get('dashboard', {}).get('page_icon', '📊'),
        layout='wide',
    )

    st.title('📊 Futures Main — Market Microstructure Analysis')

    with st.spinner('Loading data...'):
        data = load_all_data(config)

    # ── Sidebar filters ──────────────────────────────────────────────────
    st.sidebar.header('Filters')

    # Participant type filter
    all_participants = config.get('participant_types', ['Client', 'DII', 'FII', 'Pro'])
    selected_participants = st.sidebar.multiselect(
        'Participant Types', all_participants, default=all_participants)

    # ── Tabs ──────────────────────────────────────────────────────────────
    tabs = st.tabs([
        '🏛️ Participant Snapshot',
        '📈 OI Changes',
        '📊 PCR',
        '📋 Contract Positions',
        '📉 Rolling Averages',
        '🎯 Max Pain',
    ])

    # ── Tab 1: Participant Snapshot ───────────────────────────────────────
    with tabs[0]:
        st.subheader('Participant OI Snapshot')
        df = data['snapshot'].copy()
        if hasattr(df.index, 'get_level_values'):
            df = df.reset_index()

        dates = sorted(df['Date'].unique())
        if dates:
            selected_date = st.selectbox('Select Date', dates,
                                         index=len(dates) - 1,
                                         format_func=lambda d: pd.Timestamp(d).strftime('%d-%b-%Y'),
                                         key='snap_date')
            filtered = df[(df['Date'] == selected_date) &
                          (df['Client Type'].isin(selected_participants))]

            mv_cols = [c for c in filtered.columns if 'Market View' in c]
            styled = filtered.style.applymap(color_market_view, subset=mv_cols)
            st.dataframe(styled, use_container_width=True, hide_index=True)

            # Net position bar chart
            net_cols = [c for c in filtered.columns if 'Net' in c]
            if net_cols:
                st.subheader('Net Positions')
                net_data = filtered[['Client Type'] + net_cols].melt(
                    id_vars='Client Type', var_name='Instrument', value_name='Net Position')
                fig = px.bar(net_data, x='Instrument', y='Net Position',
                             color='Client Type', barmode='group',
                             color_discrete_sequence=px.colors.qualitative.Set2)
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)

    # ── Tab 2: OI Changes ────────────────────────────────────────────────
    with tabs[1]:
        st.subheader('Period-on-Period OI Changes & Volume Ratios')
        df = data['diff'].copy()
        if hasattr(df.index, 'get_level_values'):
            df = df.reset_index()

        dates = sorted(df['Date'].unique())
        if dates:
            selected_date = st.selectbox('Select Date', dates,
                                         index=len(dates) - 1,
                                         format_func=lambda d: pd.Timestamp(d).strftime('%d-%b-%Y'),
                                         key='diff_date')
            filtered = df[(df['Date'] == selected_date) &
                          (df['Client Type'].isin(selected_participants))]

            mv_cols = [c for c in filtered.columns if 'Market View' in c]
            styled = filtered.style.applymap(color_market_view, subset=mv_cols)
            st.dataframe(styled, use_container_width=True, hide_index=True)

    # ── Tab 3: PCR ───────────────────────────────────────────────────────
    with tabs[2]:
        st.subheader('Put-Call Ratio (PCR)')
        df_pcr = data['pcr'].copy()
        if not df_pcr.empty:
            fig = go.Figure()
            for col in df_pcr.columns:
                fig.add_trace(go.Scatter(x=df_pcr.index, y=df_pcr[col],
                                         mode='lines+markers', name=col))
            fig.update_layout(
                yaxis_title='PCR',
                xaxis_title='Date',
                height=400,
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

            st.dataframe(df_pcr, use_container_width=True)
        else:
            st.info('No PCR data available.')

    # ── Tab 4: Contract Positions ────────────────────────────────────────
    with tabs[3]:
        st.subheader('Contract Position Classification')
        df_pos = data['positions']
        if df_pos is not None:
            # Filters
            symbols = sorted(df_pos['SYMBOL'].unique())
            selected_symbol = st.selectbox('Symbol', symbols, key='pos_symbol')
            instruments = sorted(df_pos['INSTRUMENT'].unique())
            selected_instrument = st.selectbox('Instrument', instruments, key='pos_instrument')

            filtered = df_pos[(df_pos['SYMBOL'] == selected_symbol) &
                              (df_pos['INSTRUMENT'] == selected_instrument)]

            if not filtered.empty:
                display_cols = ['TIMESTAMP', 'EXPIRY_DT', 'STRIKE_PR', 'OPTION_TYP',
                                'CLOSE', 'OPEN_INT', 'CHG_IN_OI', 'CONTRACTS',
                                'PRICE_CHANGE', 'Position', 'Big Position']
                existing_cols = [c for c in display_cols if c in filtered.columns]
                st.dataframe(filtered[existing_cols].sort_values('TIMESTAMP', ascending=False),
                             use_container_width=True, hide_index=True)

                # Position distribution pie chart
                pos_counts = filtered['Position'].value_counts()
                fig = px.pie(values=pos_counts.values, names=pos_counts.index,
                             title='Position Distribution',
                             color_discrete_sequence=px.colors.qualitative.Pastel)
                fig.update_layout(height=350)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info('No data for selected filters.')
        else:
            st.warning('Contract data not available. Place fo*.zip files in the data directory.')

    # ── Tab 5: Rolling Averages ──────────────────────────────────────────
    with tabs[4]:
        st.subheader('Rolling Averages')
        df_roll = data['rolling']
        if df_roll is not None:
            symbols = sorted(df_roll['SYMBOL'].unique())
            selected_symbol = st.selectbox('Symbol', symbols, key='roll_symbol')
            instruments = sorted(df_roll['INSTRUMENT'].unique())
            selected_instrument = st.selectbox('Instrument', instruments, key='roll_instrument')

            filtered = df_roll[(df_roll['SYMBOL'] == selected_symbol) &
                               (df_roll['INSTRUMENT'] == selected_instrument)]

            if not filtered.empty:
                # Find rolling avg columns
                ra_cols = [c for c in filtered.columns if '_RA' in c and 'CLOSE' in c]
                if ra_cols:
                    # Pick first expiry for clean chart
                    expiries = sorted(filtered['EXPIRY_DT'].unique())
                    selected_expiry = st.selectbox('Expiry', expiries, key='roll_expiry')
                    exp_data = filtered[filtered['EXPIRY_DT'] == selected_expiry].sort_values('TIMESTAMP')

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=exp_data['TIMESTAMP'], y=exp_data['CLOSE'],
                                             mode='lines', name='Close'))
                    for col in ra_cols:
                        fig.add_trace(go.Scatter(x=exp_data['TIMESTAMP'], y=exp_data[col],
                                                  mode='lines', name=col))
                    fig.update_layout(
                        yaxis_title='Price',
                        xaxis_title='Date',
                        height=400,
                        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info('No rolling average columns found.')
            else:
                st.info('No data for selected filters.')
        else:
            st.warning('Rolling data not available.')

    # ── Tab 6: Max Pain ──────────────────────────────────────────────────
    with tabs[5]:
        st.subheader('Max Pain')
        df_mp = data['max_pain']
        if df_mp is not None and not df_mp.empty:
            st.dataframe(df_mp, use_container_width=True, hide_index=True)

            # Bar chart
            fig = px.bar(df_mp, x='SYMBOL', y='Max_Pain', color='EXPIRY_DT',
                         barmode='group', title='Max Pain by Symbol & Expiry',
                         color_discrete_sequence=px.colors.qualitative.Bold)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('No Max Pain data available. Ensure fo*.zip files with option data are present.')


if __name__ == '__main__':
    main()
