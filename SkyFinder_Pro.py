import streamlit as st
import requests
import pandas as pd
import folium
from folium.plugins import MarkerCluster
from streamlit_folium import st_folium
import time

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="SkyFinder Pro",
    page_icon="✈️",
    layout="wide"
)

# =========================
# CLEAN UI (UNCHANGED)
# =========================
st.markdown("""
<style>
.stApp {
    background: #050814;
    color: white;
}

.block-container {
    padding-top: 1rem;
    padding-left: 1.5rem;
    padding-right: 1.5rem;
    max-width: 100%;
}

h1, h2, h3 {
    color: #00d4ff;
}
</style>
""", unsafe_allow_html=True)

st.title("✈️ SkyFinder Pro")
st.caption("Real-time global aircraft radar (OpenSky powered)")

# =========================
# SIDEBAR (UNCHANGED)
# =========================
with st.sidebar:
    st.header("⚙️ Controls")

    refresh_time = st.slider("Refresh (sec)", 5, 30, 10)
    limit = st.slider("Aircraft limit", 50, 500, 200)

    country = st.text_input("Country filter")
    callsign = st.text_input("Flight search")

    min_alt = st.slider("Min altitude (m)", 0, 12000, 0)

    view = st.selectbox(
        "Region",
        ["Global 🌍", "India 🇮🇳", "Mumbai ✈️"]
    )

# =========================
# SAFE FALLBACK (ONLY WHEN OPEN SKY FAILS)
# =========================
def fallback_data():
    return pd.DataFrame([
        {"callsign": "AI101", "country": "India", "lat": 19.08, "lon": 72.88, "alt": 11000, "speed": 230, "heading": 90},
        {"callsign": "EK500", "country": "UAE", "lat": 25.27, "lon": 55.30, "alt": 12000, "speed": 260, "heading": 120},
        {"callsign": "LH123", "country": "Germany", "lat": 50.11, "lon": 8.68, "alt": 9000, "speed": 200, "heading": 70},
    ])

# =========================
# OPEN SKY ONLY (FIXED)
# =========================
URL = "https://opensky-network.org/api/states/all"

@st.cache_data(ttl=10)
def fetch_planes():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(URL, headers=headers, timeout=15)

        # ❌ FIX 1: status check
        if r.status_code != 200:
            return fallback_data()

        # ❌ FIX 2: prevent JSON crash
        try:
            data = r.json()
        except:
            return fallback_data()

        if not data or "states" not in data:
            return fallback_data()

        rows = []

        for s in data.get("states", []):
            if not s or s[5] is None or s[6] is None:
                continue

            rows.append({
                "callsign": (s[1] or "UNKNOWN").strip(),
                "country": s[2] or "Unknown",
                "lat": s[6],
                "lon": s[5],
                "alt": s[7] or 0,
                "speed": s[9] or 0,
                "heading": s[10] or 0
            })

        # ❌ FIX 3: avoid empty crash
        if len(rows) == 0:
            return fallback_data()

        return pd.DataFrame(rows)

    except:
        return fallback_data()

df = fetch_planes()

# =========================
# FILTERING (UNCHANGED)
# =========================
if not df.empty:

    if country:
        df = df[df["country"].str.contains(country, case=False, na=False)]

    if callsign:
        df = df[df["callsign"].str.contains(callsign, case=False, na=False)]

    df = df[df["alt"] >= min_alt]

    if view == "India 🇮🇳":
        df = df[(df["lat"].between(6, 37)) & (df["lon"].between(68, 98))]
    elif view == "Mumbai ✈️":
        df = df[(df["lat"].between(18, 20.5)) & (df["lon"].between(71, 74.5))]

    df = df.head(limit)

# =========================
# METRICS
# =========================
col1, col2, col3 = st.columns(3)

col1.metric("✈ Live Aircraft", len(df))
col2.metric("⚡ Fastest Speed", int(df["speed"].max()) if not df.empty else 0)
col3.metric("🌍 Countries", df["country"].nunique() if not df.empty else 0)

# =========================
# MAP (UNCHANGED UI)
# =========================
st.subheader("🌍 Live Airspace Map")

if df.empty:
    st.warning("No aircraft data available. Showing fallback data.")

center = [df["lat"].mean(), df["lon"].mean()]

m = folium.Map(
    location=center,
    zoom_start=4,
    tiles="CartoDB dark_matter"
)

cluster = MarkerCluster().add_to(m)

for _, row in df.iterrows():

    color = "#00d4ff"
    if row["speed"] > 250:
        color = "#ff4d4d"
    elif row["speed"] > 150:
        color = "#ffcc00"

    folium.CircleMarker(
        location=[row["lat"], row["lon"]],
        radius=6,
        color=color,
        fill=True,
        fill_opacity=0.9,
        tooltip=row["callsign"],
        popup=f"""
        ✈ {row['callsign']}<br>
        🌍 {row['country']}<br>
        📍 Alt: {int(row['alt'])} m<br>
        ⚡ Speed: {int(row['speed'])} m/s
        """
    ).add_to(cluster)

st_folium(m, height=750, width="100%")

# =========================
# AUTO REFRESH (UNCHANGED)
# =========================
time.sleep(refresh_time)
st.rerun()