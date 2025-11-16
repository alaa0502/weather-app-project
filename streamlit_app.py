import streamlit as st
import streamlit.components.v1 as components
import json
from pathlib import Path
import requests
from datetime import datetime
from dateutil import tz
import folium
from streamlit_folium import st_folium

# --- STREAMLIT PAGE CONFIG ---
st.set_page_config(
    page_title="TempTrack",
    page_icon="🌡️",
    layout="centered",
)

# --- CUSTOM CSS: SIDEBAR + BACKGROUND ---
st.markdown(
    """
    <style>
        /* Sidebar background gold */
        [data-testid="stSidebar"] {
            background-color: #F2C94C !important;
            box-shadow: 2px 0px 10px rgba(0, 0, 0, 0.12);
        }

        /* Less top padding */
        .block-container {
            padding-top: 0.5rem !important;
        }

        /* Main app background (light grey-white) */
        [data-testid="stAppViewContainer"] {
            background-color: #FAFAFA !important;
            transition: background 0.8s ease-in-out;
        }

        /* Sidebar text */
        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: #111111 !important;
            font-weight: 700 !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)
st.markdown("""
<style>

    /* LOCATION INPUT — EXACT SAME SHADE AS YOUR YELLOW CARD */
    div[data-testid="stTextInput"] > div > div > input {
        background-color: rgba(255, 230, 150, 0.25) !important;   /* identical */
        border: 1px solid rgba(255, 230, 150, 0.40) !important;   /* soft border */
        border-radius: 12px !important;                           /* same rounding */
        padding: 10px !important;
        font-size: 1.1rem !important;
    }

    /* Label above the input */
    div[data-testid="stTextInput"] > div > label {
        font-size: 1.15rem !important;
        font-weight: 600 !important;
        color: #333333 !important;
    }

</style>
""", unsafe_allow_html=True)

# --- SESSION STATE ---
if "has_weather" not in st.session_state:
    st.session_state["has_weather"] = False
if "last_city" not in st.session_state:
    st.session_state["last_city"] = ""
if "last_units" not in st.session_state:
    st.session_state["last_units"] = ""
if "last_weather" not in st.session_state:
    st.session_state["last_weather"] = None

# --- BASIC CONFIG ---
API_KEY = "cf1630d90ab616adea0cb07c50e4f770"
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
FORECAST_URL = "https://api.openweathermap.org/data/2.5/forecast"
GEO_URL = "http://ip-api.com/json"
SETTINGS_FILE = Path("settings.json")
DEFAULT_CITY = "Mississauga"
DEFAULT_UNITS = "metric"


# ===== LOAD / SAVE SETTINGS (JSON) =====
def load_settings():
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}
    else:
        cfg = {}

    cfg.setdefault("default_city", DEFAULT_CITY)
    cfg.setdefault("units", DEFAULT_UNITS)
    return cfg


def save_settings(cfg):
    SETTINGS_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


    # On Streamlit Cloud, IP-based detection returns the server location
    # (e.g., Dallas), not the user. So we just use the saved default.
    default_location = cfg["default_city"]

    city = st.text_input(
        "Location (you can keep this or edit it):",
        value=default_location,
        placeholder="e.g., Toronto,CA or Paris,FR",
    ).strip()


# ===== WIND DIRECTION HELPER =====
def wind_deg_to_compass(deg: float) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = int((deg % 360) / 45 + 0.5) % 8
    return dirs[idx]


# ===== ICON → EMOJI HELPER =====
def icon_to_emoji(icon_code: str) -> str:
    if not icon_code:
        return "🌡️"
    if icon_code.startswith("01"): return "☀️"
    if icon_code.startswith("02"): return "🌤️"
    if icon_code.startswith(("03", "04")): return "☁️"
    if icon_code.startswith(("09", "10")): return "🌧️"
    if icon_code.startswith("11"): return "⛈️"
    if icon_code.startswith("13"): return "❄️"
    if icon_code.startswith("50"): return "🌫️"
    return "🌡️"


# ===== FETCH WEATHER (CURRENT) =====
def fetch_weather(city, api_key, units):
    r = requests.get(
        BASE_URL,
        params={"q": city, "appid": api_key, "units": units},
        timeout=20,
    )
    r.raise_for_status()
    d = r.json()

    wind_raw = d.get("wind", {})
    wind_speed_raw = wind_raw.get("speed", 0.0)
    wind_deg = wind_raw.get("deg", 0.0)

    if units == "metric":
        wind_speed = wind_speed_raw * 3.6
        wind_unit = "km/h"
    else:
        wind_speed = wind_speed_raw
        wind_unit = "mph"

    return {
        "city": f"{d['name']}, {d['sys'].get('country', '')}",
        "lat": d["coord"]["lat"],
        "lon": d["coord"]["lon"],
        "temp": d["main"]["temp"],
        "feels_like": d["main"]["feels_like"],
        "humidity": d["main"]["humidity"],
        "condition": d["weather"][0]["description"].title(),
        "icon": d["weather"][0]["icon"],
        "timezone_seconds": d.get("timezone", 0),
        "wind_speed": wind_speed,
        "wind_unit": wind_unit,
        "wind_deg": wind_deg,
        "wind_dir": wind_deg_to_compass(wind_deg),
    }


# ===== FETCH WEEKLY FORECAST =====
def fetch_weekly_forecast(lat, lon):
    r = requests.get(
        FORECAST_URL,
        params={
            "lat": lat,
            "lon": lon,
            "appid": API_KEY,
            "units": "metric",
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()

    daily = {}
    for entry in data["list"]:
        date = entry["dt_txt"].split(" ")[0]
        temp = entry["main"]["temp"]
        icon = entry["weather"][0]["icon"]
        if date not in daily:
            daily[date] = {"temp": temp, "icon": icon}

    result = []
    for date, v in list(daily.items())[:7]:
        result.append({
            "date": date,
            "temp": int(v["temp"]),
            "icon": v["icon"]
        })

    return result


# ===== WEEKLY FORECAST SIDEBAR RENDER =====
def show_weekly_forecast(forecast, units):
    if not forecast:
        return

    st.sidebar.subheader("📅 Your Week Ahead")

    for day in forecast:
        emoji = icon_to_emoji(day["icon"])
        temp = f"{day['temp']}°{'C' if units=='metric' else 'F'}"

        st.sidebar.markdown(
            f"""
            <div style="
                background-color:#F7F7F7;
                padding:10px;
                border-radius:10px;
                margin-bottom:8px;
                text-align:center;
                font-size:1.1rem;">
                <b>{day['date']}</b><br>
                <span style="font-size:1.8rem;">{emoji}</span><br>
                {temp}
            </div>
            """,
            unsafe_allow_html=True
        )


# ===== DISPLAY WEATHER =====
def show_weather(w, units):
    deg_unit = "°C" if units == "metric" else "°F"
    icon_url = f"http://openweathermap.org/img/wn/{w['icon']}@2x.png"
    emoji = icon_to_emoji(w["icon"])

    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown(f"### 🌍 {w['city']}")
        st.write(w["condition"])
        st.write(
            f"**Wind:** {w['wind_speed']:.1f} {w['wind_unit']} "
            f"from {w['wind_dir']} ({int(w['wind_deg'])}°)"
        )

    with col_right:
        st.markdown(
            f"""
            <div style="text-align:center; font-size:2.6rem; font-weight:700;">
                {emoji} {w['temp']:.1f}{deg_unit}
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.image(icon_url, width=72)

    c1, c2 = st.columns(2)
    c1.metric("Feels Like", f"{w['feels_like']:.1f}{deg_unit}")
    c2.metric("Humidity", f"{w['humidity']}%")

    user_now = datetime.now().astimezone()
    utc_now = datetime.now(tz=tz.tzutc())
    loc_now = utc_now.astimezone(tz.tzoffset(None, w["timezone_seconds"]))

    st.write("**Your time:**", user_now.strftime("%A, %b %d, %I:%M %p %Z"))
    st.write("**Location time:**", loc_now.strftime("%A, %b %d, %I:%M %p"))


# ===== HISTORICAL AVERAGE =====
def fetch_historical_average(lat, lon):
    today = datetime.now()
    month = today.month
    day = today.day

    start_year = today.year - 10
    end_year = today.year - 1

    url = (
        "https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={start_year}-{month:02d}-{day:02d}"
        f"&end_date={end_year}-{month:02d}-{day:02d}"
        "&daily=temperature_2m_mean"
        "&timezone=auto"
    )

    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        data = r.json()
        temps = data.get("daily", {}).get("temperature_2m_mean", [])
        if not temps:
            return None
        return sum(temps) / len(temps)
    except Exception:
        return None


# ===== FRIENDLY COMPARISON (NO TITLE + YELLOW CARD) =====
def show_historical_comparison(w, units):
    lat = w["lat"]
    lon = w["lon"]
    current_temp = w["temp"]

    avg_temp_c = fetch_historical_average(lat, lon)
    if avg_temp_c is None:
        return

    if units == "metric":
        avg_display = avg_temp_c
        diff = current_temp - avg_display
        unit_label = "°C"
    else:
        avg_display = avg_temp_c * 9.0 / 5.0 + 32.0
        diff = current_temp - avg_display
        unit_label = "°F"

    box_style = (
        "background-color: rgba(255, 230, 150, 0.25);"
        "padding: 15px;"
        "border-radius: 12px;"
        "margin-top: 10px;"
        "margin-bottom: 15px;"
        "text-align: center;"
        "font-size: 1.15rem;"
        "line-height: 1.5;"
    )

    if abs(diff) < 1:
        msg = (
            f"<b>🌤️ Pretty typical for this time of year</b><br>"
            f"Average for today: {avg_display:.1f}{unit_label}"
        )
    elif diff > 0:
        msg = (
            f"<b>🔥 Warmer than usual today</b><br>"
            f"About {diff:.1f}{unit_label} warmer than the usual {avg_display:.1f}{unit_label}."
        )
    else:
        msg = (
            f"<b>❄️ Colder than usual today</b><br>"
            f"About {abs(diff):.1f}{unit_label} colder than the usual {avg_display:.1f}{unit_label}."
        )

    st.markdown(f"<div style='{box_style}'>{msg}</div>", unsafe_allow_html=True)


# ===== SIMPLE LOCATION MAP =====
def show_location_map(w):
    st.subheader("🗺 City location")
    st.map({"lat": [w["lat"]], "lon": [w["lon"]]}, zoom=10)


# ===== WIND MAP =====
def show_wind_map_pretty(lat, lon):
    windy_html = f"""
    <iframe width="700" height="550"
        src="https://embed.windy.com/embed2.html?lat={lat}&lon={lon}
        &detailLat={lat}&detailLon={lon}
        &zoom=7&level=surface&overlay=wind&menu=&message=true&marker=true"
        frameborder="0">
    </iframe>
    """
    components.html(windy_html, height=550)


# ===== RADAR MAP =====
def show_radar_map(lat, lon):
    st.subheader("🌧 Radar view")

    m = folium.Map(location=[lat, lon], zoom_start=7)

    folium.raster_layers.TileLayer(
        tiles=(
            "https://tilecache.rainviewer.com/v2/radar/nowcast_0/512/{z}/{x}/{y}/2/1_1.png"
        ),
        attr="RainViewer",
        name="Rain Radar",
        opacity=0.8,
        overlay=True,
        control=True,
    ).add_to(m)

    folium.Marker([lat, lon], popup="Selected location").add_to(m)

    st_folium(m, width=700, height=550)


# ===== MAIN APP =====
def main():
    cfg = load_settings()

    # Logo centered
    st.markdown("<div style='text-align:center;'>", unsafe_allow_html=True)
    st.image("logo.png", width=380)
    st.markdown("</div>", unsafe_allow_html=True)

    # Sidebar settings
    st.sidebar.header("Settings")

    units_label = st.sidebar.radio(
        "Temperature Units",
        ["Metric (°C)", "Imperial (°F)"],
        index=0 if cfg["units"] == "metric" else 1,
    )
    units = "metric" if units_label.startswith("Metric") else "imperial"
    cfg["units"] = units

    map_mode = st.sidebar.radio(
        "Map View",
        ["Location only", "Wind map (live)", "Radar view (live)"],
        index=0,
    )

    save_settings(cfg)

    st.subheader("Choose a location")

    detected_city = detect_city_from_ip()
    default_location = detected_city or cfg["default_city"]

    city = st.text_input(
        "Location (you can keep this or edit it):",
        value=default_location,
    ).strip()

    if city:
        st.write(f"➡️ Using location: **{city}**")
        cfg["default_city"] = city
        save_settings(cfg)
    else:
        st.write("➡️ Please enter a city (e.g., `Lod,IL`).")

    weather_to_show = None
    pressed = st.button("Get Weather")

    auto_refresh = (
        st.session_state["has_weather"]
        and city
        and city == st.session_state["last_city"]
        and units != st.session_state["last_units"]
    )

    try:
        if (pressed and city) or (auto_refresh and city):
            w = fetch_weather(city, API_KEY, units)
            st.session_state["has_weather"] = True
            st.session_state["last_city"] = city
            st.session_state["last_units"] = units
            st.session_state["last_weather"] = w
            weather_to_show = w

        elif (
            st.session_state["has_weather"]
            and city
            and city == st.session_state["last_city"]
            and units == st.session_state["last_units"]
            and st.session_state["last_weather"] is not None
        ):
            weather_to_show = st.session_state["last_weather"]

    except Exception as e:
        st.error(f"Error: {e}")

    # --- SHOW CURRENT WEATHER + FORECAST ---
    if weather_to_show:

        # Show forecast in sidebar
        forecast = fetch_weekly_forecast(weather_to_show["lat"], weather_to_show["lon"])
        show_weekly_forecast(forecast, units)

        st.divider()
        show_weather(weather_to_show, units)

        st.divider()
        show_historical_comparison(weather_to_show, units)

        st.divider()
        if map_mode == "Location only":
            show_location_map(weather_to_show)
        elif map_mode == "Wind map (live)":
            show_wind_map_pretty(weather_to_show["lat"], weather_to_show["lon"])
        else:
            show_radar_map(weather_to_show["lat"], weather_to_show["lon"])


if __name__ == "__main__":
    main()
