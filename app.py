#!/usr/bin/env python3
# coding: utf-8

"""
Streamlit app for fetching MLB standings, automatically logging daily win totals,
and displaying interactive bar and line charts with selectable history windows.
Zero-click logging: every page load logs today's totals once.
"""
import os
from datetime import datetime
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# Constants
STANDINGS_URL = (
    "https://bdfed.stitch.mlbinfra.com/bdfed/transform-mlb-standings"
    "?splitPcts=false&numberPcts=false&standingsView=division"
    "&sortTemplate=3&season=2025&leagueIds=103&leagueIds=104"
    "&standingsTypes=regularSeason&hydrateAlias=noSchedule"
    "&sortDivisions=201,202,200,204,205,203"
    "&sortLeagues=103,104,115,114&sortSports=1"
)
CSV_PATH = "wins_history.csv"

# Participant-to-team index mapping
PARTICIPANT_TEAMS = {
    'Nick':    [0, 10, 18, 7, 19],
    'Doug':    [4, 8, 5, 23, 12],
    'Ryan Hi': [27, 25, 13, 24, 14],
    'Peter':   [1, 20, 26, 22, 9],
    'Ryan Hu': [15, 16, 3, 21, 29],
    'Colin':   [28, 11, 2, 6, 17],
}

@st.cache_data
def fetch_standings(url: str) -> pd.DataFrame:
    response = requests.get(url)
    response.raise_for_status()
    payload = response.json()
    rows = []
    for division in payload.get('records', []):
        for team in division.get('teamRecords', []):
            rows.append({'team': team['name'], 'wins': team['wins'], 'losses': team['losses']})
    return pd.DataFrame(rows)

# no caching on load_history so writes show immediately
def load_history(csv_path: str) -> pd.DataFrame:
    if os.path.isfile(csv_path) and os.path.getsize(csv_path) > 0:
        df = pd.read_csv(csv_path, parse_dates=['date'])
        df.set_index('date', inplace=True)
        return df
    return pd.DataFrame()


def calculate_totals(df: pd.DataFrame) -> pd.Series:
    totals = {}
    for participant, idxs in PARTICIPANT_TEAMS.items():
        valid = [i for i in idxs if 0 <= i < len(df)]
        totals[participant] = df.iloc[valid]['wins'].sum()
    return pd.Series(totals, name='Win Total')


def log_win_totals(totals: pd.Series, csv_path: str) -> bool:
    """
    Append today's totals to CSV if not already present. Return True if added.
    """
    today_str = datetime.today().strftime('%Y-%m-%d')
    today_dt = pd.to_datetime(today_str)
    history = load_history(csv_path)

    if not history.empty and today_dt in history.index:
        return False
    entry = pd.DataFrame([totals.to_dict()], index=[today_dt])
    combined = pd.concat([history, entry])
    combined.to_csv(csv_path, index_label='date')
    return True


def main():
    st.title("MLB Wins Pool Tracker")

    # 1) Fetch latest standings and calculate totals
    standings_df = fetch_standings(STANDINGS_URL)
    totals = calculate_totals(standings_df)

    # 2) Auto-log today's totals once per day
    added = log_win_totals(totals, CSV_PATH)
    if added:
        st.success("Today's win totals have been logged automatically.")
    else:
        st.info("Win totals for today were already logged.")

    # 3) Optional raw standings table
    if st.checkbox("Show MLB Standings Table"):
        st.dataframe(standings_df)

    # 4) Bar chart of current totals
    st.subheader("Current Participant Win Totals")
    fig1, ax1 = plt.subplots()
    totals.sort_values(ascending=False).plot(kind='bar', ax=ax1, rot=45)
    ax1.bar_label(ax1.containers[0])
    ax1.set_ylabel('Win Total')
    st.pyplot(fig1)
    plt.close(fig1)

    # 5) Selectable history window and line chart
    history = load_history(CSV_PATH)
    if not history.empty:
        choice = st.radio(
            "Select history window (days)",
            options=[7, 14, 30],
            index=2,
            format_func=lambda x: f"Last {x} days"
        )
        window_df = history.last(f"{choice}D")

        st.subheader(f"Participant Win Totals Over the Last {choice} Days")
        fig2, ax2 = plt.subplots(figsize=(10, 5))
        window_df.plot(ax=ax2, linewidth=2)
        ax2.set_ylabel('Total Wins')
        ax2.set_xlabel('Date')
        ax2.grid(True, linestyle='--', alpha=0.5)
        st.pyplot(fig2)
        plt.close(fig2)
    else:
        st.info("No historical data available.")

if __name__ == "__main__":
    main()
