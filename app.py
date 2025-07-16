#!/usr/bin/env python3
# coding: utf-8

"""
Streamlit app for fetching MLB standings, displaying and logging participant win totals,
with interactive bar and line charts.
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

@st.cache_data
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

def log_win_totals(totals: pd.Series, csv_path: str) -> None:
    today = datetime.today().strftime('%Y-%m-%d')
    entry = {'date': today, **totals.to_dict()}
    hist = load_history(csv_path)
    combined = pd.concat([hist, pd.DataFrame([entry]).set_index(pd.to_datetime([today]))])
    combined.to_csv(csv_path, index_label='date')

def main():
    st.title("MLB Wins Pool Tracker")
    # Fetch and calculate
    standings_df = fetch_standings(STANDINGS_URL)
    totals = calculate_totals(standings_df)

    # Display raw standings table
    if st.checkbox("Show MLB Standings Table"):
        st.dataframe(standings_df)

    # Bar chart of current totals
    st.subheader("Current Participant Win Totals")
    fig1, ax1 = plt.subplots()
    totals.sort_values(ascending=False).plot(kind='bar', ax=ax1, rot=45)
    ax1.bar_label(ax1.containers[0])
    ax1.set_ylabel('Win Total')
    st.pyplot(fig1)

    # Log new entry when user clicks button
    if st.button("Log Today's Totals"):
        log_win_totals(totals, CSV_PATH)
        st.success(f"Logged totals to {CSV_PATH}")

    # Line chart of history
    history = load_history(CSV_PATH)
    if not history.empty:
        st.subheader("Participant Win Totals Over Time")
        fig2, ax2 = plt.subplots()
        history.plot(marker='o', ax=ax2)
        ax2.set_ylabel('Total Wins')
        ax2.set_xlabel('Date')
        st.pyplot(fig2)
    else:
        st.info("No historical data found. Click 'Log Today's Totals' to create the history.")

if __name__ == "__main__":
    main()
