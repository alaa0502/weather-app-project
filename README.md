# 🌡️ TempTrack – Simple Weather App

## TempTrack is a Streamlit-based weather app - a required first project of my Data science cource with a few added features of my own.
## It shows real-time weather, a 7-day forecast, interactive maps, and a friendly “warmer/colder than usual” comparison based on 10-year climate data.

## 👉 Try the app:
https://weather-app-project-temptrack.streamlit.app/


![App Screenshot](Weatherapp.png)


## Features

- Current temperature, humidity, wind, and weather description

- Local time and the time in the selected location

- Forecast a week ahead

- Location map, wind map, and radar view

- 10-year average temperature comparison for today ("warmer\ colder than usual")

- Saves your last used location
  
- choose units (°C / °F)
  
## Limitations

-I wanted the app to automatically use the user’s real location as the default, but this requires paid APIs, so it isn’t supported.

-Some advanced features (hourly forecasts, weather alerts, more interactive maps, etc.) require paid plans so I did not include them.

## Project Structure

streamlit_app.py     # Main application
logo.png             # Logo of app
Weatherapp.png       # app preview above
settings.json        # Stored user preferences
requirements.txt     # Dependencies

## Skills Used:
- Python (basic scripting)
  
- Working with JSON and REST APIs
  
- Timezone and datetime handling
  
- Simple file I/O (JSON settings)
  
- Streamlit UI development
  
- Folium and Streamlit-Folium for maps

## Run Locally
pip install -r requirements.txt
streamlit run streamlit_app.py

## Requirements
streamlit

requests

python-dateutil

folium

streamlit-folium
