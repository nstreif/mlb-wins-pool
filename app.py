#!/usr/bin/env python3
# coding: utf-8

"""
Streamlit app for fetching MLB standings and displaying interactive bar and line charts.
Historical win totals are fetched live from the MLB API (no CSV).
"""
from datetime import datetime, timedelta
import requests
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import os


# Constants
BASE_URL = (
    "https://bdfed.stitch.mlbinfra.com/bdfed/transform-mlb-standings"
    "?splitPcts=false&numberPcts=false&standingsView=division"
    "&sortTemplate=3&season=2025&leagueIds=103&leagueIds=104"
    "&standingsTypes=regularSeason&hydrateAlias=noSchedule"
    "&sortDivisions=201,202,200,204,205,203"
    "&sortLeagues=103,104,115,114&sortSports=1"
)

# Participant-to-team index mapping
PARTICIPANT_TEAMS = {
    'Nick':    [0, 10, 18, 7, 19],
    'Doug':    [4, 8, 5, 23, 12],
    'Ryan Hi': [27, 25, 13, 24, 14],
    'Peter':   [1, 20, 26, 22, 9],
    'Ryan Hu': [15, 16, 3, 21, 29],
    'Colin':   [28, 11, 2, 6, 17],
}

BANNER_PATH = "banner.png"

@st.cache_data
def fetch_standings_for_date(date_str: str) -> pd.DataFrame:
    """Fetch MLB standings for a specific date."""
    url = f"{BASE_URL}&date={date_str}"
    response = requests.get(url)
    response.raise_for_status()
    payload = response.json()
    rows = []
    for division in payload.get('records', []):
        for team in division.get('teamRecords', []):
            rows.append({'team': team['name'], 'wins': team['wins'], 'losses': team['losses']})
    return pd.DataFrame(rows)

def calculate_totals(df: pd.DataFrame) -> pd.Series:
    """Calculate win totals for each participant based on their team selections."""
    totals = {}
    for participant, idxs in PARTICIPANT_TEAMS.items():
        valid = [i for i in idxs if 0 <= i < len(df)]
        totals[participant] = df.iloc[valid]['wins'].sum()
    return pd.Series(totals, name='Win Total')

@st.cache_data
def fetch_history(start_date: str, end_date: str) -> pd.DataFrame:
    """Fetch historical win totals for a date range."""
    start = datetime.fromisoformat(start_date).date()
    end = datetime.fromisoformat(end_date).date()
    days = (end - start).days + 1
    history = []
    
    # Show progress bar while fetching data
    progress_bar = st.progress(0)
    for i in range(days):
        progress = (i + 1) / days
        progress_bar.progress(progress)
        
        d = start + timedelta(days=i)
        ds = d.isoformat()
        try:
            standings = fetch_standings_for_date(ds)
            totals = calculate_totals(standings)
            entry = {**totals.to_dict(), 'date': ds}
            history.append(entry)
        except Exception as e:
            st.warning(f"Could not fetch data for {ds}: {str(e)}")
            continue
    
    progress_bar.empty()
    
    df = pd.DataFrame(history)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
    return df

def main():
    if os.path.isfile(BANNER_PATH):
        st.image(BANNER_PATH, use_container_width=True)

    st.title("MLB Wins Pool Tracker")
    
    today = datetime.today()
    end_date = today.date()
    
    # Fetch current standings
    try:
        standings_df = fetch_standings_for_date(end_date.isoformat())
        totals = calculate_totals(standings_df)
        
        # Optional display of raw standings
        if st.checkbox("Show MLB Standings Table"):
            st.dataframe(standings_df)
        
        # Bar chart of current totals
        st.subheader("Current Participant Win Totals")
        fig1, ax1 = plt.subplots()
        totals.sort_values(ascending=False).plot(kind='bar', ax=ax1, rot=45)
        ax1.bar_label(ax1.containers[0])
        ax1.set_ylabel('Win Total')
        st.pyplot(fig1)
        
        # Line chart of history
        st.subheader("Participant Win Totals Over Time")
        
        # Time range selector
        time_range = st.radio(
            "Select time range:",
            ["Past 30 Days", "Past 14 Days", "Past Week"],
            horizontal=True,
            index=0  # Select first option (Past 30 Days) by default
        )
        
        # Calculate start date based on selection
        if time_range == "Past Week":
            start_date = (today - timedelta(days=7)).date()
        elif time_range == "Past 14 Days":
            start_date = (today - timedelta(days=14)).date()
        else:  # Past 30 Days
            start_date = (today - timedelta(days=30)).date()
        with st.spinner("Fetching historical data..."):
            history = fetch_history(start_date.isoformat(), end_date.isoformat())
        
        if not history.empty:
            fig2, ax2 = plt.subplots()
            history.plot(marker='', ax=ax2)
            ax2.set_ylabel('Total Wins')
            ax2.set_xlabel('Date')
            st.pyplot(fig2)
        else:
            st.info("No historical data available for the selected range.")
            
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")

if __name__ == "__main__":
    main()
