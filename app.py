# --- Weather Checker (console) ---
# Run in PyCharm: Right-click > Run 'app'
# Requires: pip install requests python-dateutil

import json
from pathlib import Path
from datetime import datetime
from dateutil import tz
import requests

# ====== CONFIG ======
API_KEY = "cf1630d90ab616adea0cb07c50e4f770"   # replace with your key if needed
BASE_URL = "https://api.openweathermap.org/data/2.5/weather"
GEO_URL = "http://ip-api.com/json"  # for IP-based location

SETTINGS_FILE = Path("settings.json")
DEFAULT_CITY = "Mississauga"
DEFAULT_UNITS = "metric"  # "metric" (°C) or "imperial" (°F)


# ====== SETTINGS (JSON on disk) ======
def load_settings():
    cfg = {}
    if SETTINGS_FILE.exists():
        try:
            cfg = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        except Exception:
            cfg = {}

    # backwards compatibility: convert "favorites" -> "saved_locations"
    if "favorites" in cfg and "saved_locations" not in cfg:
        cfg["saved_locations"] = cfg["favorites"]

    cfg.setdefault("default_city", DEFAULT_CITY)
    cfg.setdefault("saved_locations", [DEFAULT_CITY])
    cfg.setdefault("units", DEFAULT_UNITS)
    return cfg


def save_settings(cfg: dict):
    SETTINGS_FILE.write_text(
        json.dumps(cfg, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ====== GEOLOCATION: detect city from IP ======
def detect_city_from_ip():
    """
    Try to detect user's city from their IP address.
    Returns a string like 'Mississauga,CA' or None if it fails.
    """
    try:
        r = requests.get(GEO_URL, timeout=5)
        r.raise_for_status()
        data = r.json()

        if data.get("status") == "success":
            city = data.get("city")
            country_code = data.get("countryCode")  # e.g., CA, IL
            if city and country_code:
                return f"{city},{country_code}"
            return city
    except Exception:
        pass

    return None


# ====== CORE: call REST API and parse JSON ======
def fetch_weather(city: str, api_key: str, units: str):
    if not api_key or "PASTE_YOUR_OPENWEATHERMAP_KEY_HERE" in api_key:
        raise RuntimeError("Missing OpenWeatherMap API key.")

    params = {"q": city, "appid": api_key, "units": units}
    r = requests.get(BASE_URL, params=params, timeout=20)
    r.raise_for_status()
    d = r.json()  # JSON -> dict

    result = {
        "city": f"{d['name']}, {d['sys'].get('country', '')}",
        "lat": d["coord"]["lat"],
        "lon": d["coord"]["lon"],
        "temp": d["main"]["temp"],
        "feels_like": d["main"]["feels_like"],
        "humidity": d["main"]["humidity"],
        "condition": d["weather"][0]["description"].title(),
        "icon": d["weather"][0]["icon"],
        "timezone_seconds": d.get("timezone", 0),  # offset from UTC
        "raw": d,
    }
    return result


# ====== UI helpers (console) ======
def prompt_city_and_units(cfg: dict):
    # Try to detect location automatically
    detected_city = detect_city_from_ip()

    # Which city will we suggest?
    suggested_city = detected_city or cfg["default_city"]

    print()
    if detected_city:
        print(f"Detected location (by IP): {detected_city}")
    else:
        print(f"Could not detect location automatically. Using default: {cfg['default_city']}")

    print("Saved locations:", ", ".join(cfg["saved_locations"]))
    city = input(f"Enter city (ENTER for detected/default: {suggested_city}): ").strip()
    if not city:
        city = suggested_city

    # Allow user to change units
    u = input("Units m=metric(°C), i=imperial(°F) [ENTER keep current]: ").strip().lower()
    if u == "m":
        cfg["units"] = "metric"
    elif u == "i":
        cfg["units"] = "imperial"

    # Update saved_locations list
    if city not in cfg["saved_locations"]:
        cfg["saved_locations"].append(city)

    # Optionally update default city to the last used one
    cfg["default_city"] = city

    save_settings(cfg)
    return city, cfg["units"]


def show_weather(w: dict, units: str):
    deg = "°C" if units == "metric" else "°F"
    print("—" * 60)
    print("Weather for:", w["city"])
    print(f"Temp: {w['temp']}{deg}  | Feels: {w['feels_like']}{deg}  | Humidity: {w['humidity']}%")
    print("Condition:", w["condition"])
    print(f"Coords: ({w['lat']:.3f}, {w['lon']:.3f})")
    print("—" * 60)


def print_times(w: dict):
    # your local time
    user_now = datetime.now().astimezone()
    user_str = user_now.strftime("%A, %b %d, %Y %I:%M %p %Z")

    # location time via fixed offset from API
    utc_now = datetime.now(tz=tz.tzutc())
    loc_now = utc_now.astimezone(tz.tzoffset(None, w["timezone_seconds"]))
    loc_str = loc_now.strftime("%A, %b %d, %Y %I:%M %p %Z")

    print("Your local time :", user_str)
    print(f"{w['city']} time :", loc_str)
def fetch_historical_average(lat, lon):
    """Get 10-year average temperature for today's date using Open-Meteo."""
    today = datetime.now()
    month = today.month
    day = today.day

    start_year = today.year - 10
    end_year = today.year - 1  # last year only

    # Build API call
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

        avg_temp = sum(temps) / len(temps)
        return avg_temp

    except Exception:
        return None
def show_historical_comparison(current_temp, lat, lon):
    avg_temp = fetch_historical_average(lat, lon)

    if avg_temp is None:
        st.info("Historical climate data is not available for this location.")
        return

    diff = current_temp - avg_temp

    if abs(diff) < 1:
        st.success("🌤 Today’s temperature is typical for this date.")
    elif diff > 0:
        st.warning(f"🔥 Today is {diff:.1f}°C warmer than usual for this date (10-year avg: {avg_temp:.1f}°C).")
    else:
        st.info(f"❄️ Today is {abs(diff):.1f}°C colder than usual for this date (10-year avg: {avg_temp:.1f}°C).")


# ====== MAIN ======
def main():
    cfg = load_settings()
    save_settings(cfg)  # ensure file exists and is normalized

    city, units = prompt_city_and_units(cfg)

    try:
        weather = fetch_weather(city, api_key=API_KEY, units=units)
        show_weather(weather, units)
        print_times(weather)
        # (Optional) show raw JSON keys for learning:
        print("Raw JSON keys:", list(weather["raw"].keys()))
    except requests.HTTPError as e:
        print("HTTP error:", e.response.text[:300])
    except Exception as e:
        print("Error:", e)


if __name__ == "__main__":
    main()
