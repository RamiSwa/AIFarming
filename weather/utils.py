import pandas as pd
from .models import WeatherData
import requests_cache
from retry_requests import retry
import openmeteo_requests
import requests
from django.conf import settings

# Set up caching and retry logic for Open-Meteo requests
cache_session = requests_cache.CachedSession('.cache', expire_after=3600)
retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
openmeteo = openmeteo_requests.Client(session=retry_session)

def save_weather_data(weather_data, original_location=None):
    """
    Save or update weather data in the database.
    Parameters:
    - weather_data (pd.DataFrame): DataFrame containing weather data.
    - original_location (str): Original location name, if provided.
    """
    for _, row in weather_data.iterrows():
        try:
            WeatherData.objects.update_or_create(
                time=row['time'], location=row['location'], latitude=row["latitude"], longitude=row["longitude"],
                defaults={
                    'original_location': original_location,
                    'temperature_2m': row['temperature_2m'],
                    'relative_humidity_2m': row['relative_humidity_2m'],
                    'wind_speed_10m': row['wind_speed_10m'],
                    'precipitation': row['precipitation'],
                }
            )
        except WeatherData.MultipleObjectsReturned:
            print(f"⚠️ Duplicate entry detected for {row['time']} at {row['location']}. Skipping update.")




def fetch_weather_data_from_openmeteo(latitude, longitude):
    """
    Fetch real-time weather data from Open-Meteo for a specific location.
    Parameters:
    - latitude (float): Latitude of the location.
    - longitude (float): Longitude of the location.
    Returns:
    - pd.DataFrame: DataFrame containing hourly weather data.
    """
    try:
        # Open-Meteo API parameters
        params = {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "temperature_2m,relative_humidity_2m,wind_speed_10m,precipitation",
            "timezone": "auto",
        }
        response = openmeteo.weather_api("https://api.open-meteo.com/v1/forecast", params=params)[0]

        # Process hourly data
        hourly = response.Hourly()
        hourly_data = {
            "time": pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            ),
            "temperature_2m": hourly.Variables(0).ValuesAsNumpy(),
            "relative_humidity_2m": hourly.Variables(1).ValuesAsNumpy(),
            "wind_speed_10m": hourly.Variables(2).ValuesAsNumpy(),
            "precipitation": hourly.Variables(3).ValuesAsNumpy(),
        }

        weather_df = pd.DataFrame(hourly_data)
        weather_df["location"] = f"{latitude},{longitude}"
        weather_df["latitude"] = latitude
        weather_df["longitude"] = longitude

        return weather_df

    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return pd.DataFrame()




def geocode_location(location_name):
    """
    Fetch latitude and longitude for a given location name using OpenCage Geocoder.
    Parameters:
    - location_name (str): Name of the location (e.g., "Berlin").
    Returns:
    - dict: A dictionary with 'latitude' and 'longitude'.
    """
    try:
        # Replace with your OpenCage Geocoder API key
        API_KEY = settings.OPENCAGE_API_KEY  # ✅ Use Django settings
        if not API_KEY:
            raise ValueError("Missing OpenCage API Key. Check .env file.")
        url = f"https://api.opencagedata.com/geocode/v1/json?q={location_name}&key={API_KEY}"

        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors

        data = response.json()
        if data['results']:
            coordinates = data['results'][0]['geometry']
            return {"latitude": coordinates['lat'], "longitude": coordinates['lng']}
        else:
            raise ValueError(f"No results found for location: {location_name}")

    except Exception as e:
        print(f"Error in geocoding: {e}")
        return None



