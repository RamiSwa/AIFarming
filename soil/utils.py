import pandas as pd
from .models import SoilData
import requests
from django.utils.timezone import localtime
import logging
from django.conf import settings

# Setup logger
logger = logging.getLogger(__name__)

def validate_soil_data(data):
    """
    Validate soil data before saving it.
    Ensures required fields are present and values are within expected ranges.
    """
    errors = []

    required_fields = ["time", "location", "latitude", "longitude", "soil_temp_0_to_7cm", "soil_temp_7_to_28cm"]
    for field in required_fields:
        if field not in data or data[field] in [None, "", "null"]:
            errors.append(f"Missing required field: {field}")

    # Validate numerical values (ensure they are floats and within a reasonable range)
    try:
        if not -50 <= float(data["soil_temp_0_to_7cm"]) <= 60:
            errors.append("Invalid soil temperature (0-7cm) value. Must be between -50 and 60°C.")
    except (ValueError, TypeError):
        errors.append("Soil temperature (0-7cm) must be a valid number.")

    try:
        if not -50 <= float(data["soil_temp_7_to_28cm"]) <= 60:
            errors.append("Invalid soil temperature (7-28cm) value. Must be between -50 and 60°C.")
    except (ValueError, TypeError):
        errors.append("Soil temperature (7-28cm) must be a valid number.")

    if "moisture" in data and data["moisture"] not in [None, ""]:
        try:
            if not (0 <= float(data["moisture"]) <= 100):
                errors.append("Moisture percentage must be between 0 and 100.")
        except (ValueError, TypeError):
            errors.append("Moisture must be a valid number.")

    if "ph_level" in data and data["ph_level"] not in [None, ""]:
        try:
            if not (0 <= float(data["ph_level"]) <= 14):
                errors.append("pH level must be between 0 and 14.")
        except (ValueError, TypeError):
            errors.append("pH level must be a valid number.")

    # Validate latitude & longitude
    try:
        float(data["latitude"])
        float(data["longitude"])
    except (ValueError, TypeError):
        errors.append("Invalid latitude or longitude values.")

    if errors:
        return errors  # Return the list of validation errors
    return None  # ✅ Return None if validation passes

def save_soil_data(soil_data, original_location=None, data_source="manual", user=None, sensor_type=None):
    """
    Save or update soil data in the database with proper handling for missing values.
    """
    for _, row in soil_data.iterrows():
        try:
            # Log received data
            logger.info(f"Processing soil data: {row.to_dict()}")

            # Ensure latitude & longitude are present
            if "latitude" not in row or "longitude" not in row or row["latitude"] is None or row["longitude"] is None:
                logger.warning(f"Missing coordinates, attempting geolocation for {row['location']}")
                geocode_result = geocode_location(row["location"])
                
                if geocode_result:
                    row["latitude"] = geocode_result["latitude"]
                    row["longitude"] = geocode_result["longitude"]
                else:
                    logger.error(f"Geocoding failed for location: {row['location']}")
                    continue  # Skip this entry if geolocation fails

            # Validate data before saving
            validation_errors = validate_soil_data(row.to_dict())
            if validation_errors:
                logger.warning(f"Skipping invalid data: {validation_errors}")
                continue  # Skip invalid entries

            # Prepare data for database entry
            soil_entry = {
                'time': row['time'],
                'location': row['location'],
                'original_location': original_location if original_location else row['location'],
                'soil_temp_0_to_7cm': row['soil_temp_0_to_7cm'],
                'soil_temp_7_to_28cm': row['soil_temp_7_to_28cm'],
                'moisture': row.get('moisture', None),
                'ph_level': row.get('ph_level', None),
                'nitrogen': row.get('nitrogen', None),
                'phosphorus': row.get('phosphorus', None),
                'potassium': row.get('potassium', None),
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'last_updated': localtime(),
                'data_source': data_source,
                'user': user if user else None,  # ✅ Ensure user is stored or set to None
                'sensor_type': sensor_type if sensor_type else None  # ✅ Ensure sensor type is stored correctly
            }

            # Save or update data
            SoilData.objects.update_or_create(
                time=row['time'], location=row['location'], user=user,
                defaults=soil_entry
            )
            logger.info(f"Soil data successfully saved for location: {row['location']} by user: {user if user else 'Anonymous'}")

        except Exception as e:
            logger.error(f"Error saving soil data: {e}")


def process_csv_data(csv_file, user=None):
    """
    Process CSV file upload, validate, and save soil data.
    """
    try:
        df = pd.read_csv(csv_file)

        required_columns = ["time", "location", "soil_temp_0_to_7cm", "soil_temp_7_to_28cm", "moisture", "ph_level", "latitude", "longitude"]
        optional_columns = ["nitrogen", "phosphorus", "potassium"]

        # ✅ Ensure column headers match exactly
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return False, f"❌ Missing required columns: {', '.join(missing_columns)}"

        # ✅ Fill missing optional columns with None
        for col in optional_columns:
            if col not in df.columns:
                df[col] = None  

        # ✅ Convert time column to datetime format
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df.dropna(subset=["time"], inplace=True)

        # ✅ Ensure each row has the correct number of columns
        if df.isnull().all(axis=1).any():
            return False, f"❌ Detected rows with missing values. Check CSV format."

        # ✅ Check for duplicate timestamps per location
        duplicates = df[df.duplicated(subset=["time", "location"], keep=False)]
        if not duplicates.empty:
            return False, f"❌ Duplicate timestamp entries found: {duplicates[['time', 'location']].to_dict(orient='records')}"

        # ✅ Validate numeric columns
        numeric_columns = required_columns[2:] + optional_columns  # All columns except "time" and "location"
        for col in numeric_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')  # Convert to numeric
                if df[col].isnull().any():
                    return False, f"❌ Invalid values detected in column: {col}"

        # ✅ Log user who uploaded CSV (if authenticated)
        user_info = user.email if user and hasattr(user, "email") else "Anonymous"
        logger.info(f"Processing CSV upload by user: {user_info}")

        # ✅ Save data
        save_soil_data(df, data_source="csv", user=user)
        return True, f"✅ CSV file processed successfully by {user_info}."

    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        return False, f"❌ Error processing CSV file: {str(e)}"


def process_sensor_data(sensor_data):
    """
    Process incoming real-time sensor data.
    Expected input:
    {
        "sensor_type": "temperature",
        "time": "2025-02-06T12:30:00Z",
        "location": "Farm 1",
        "latitude": 36.7783,
        "longitude": -119.4179,
        "value": 15.8
    }
    """
    try:
        sensor_type = sensor_data.get("sensor_type")
        if sensor_type not in ["temperature", "moisture", "ph", "nutrients"]:
            return False, "Invalid sensor type."

        # Map sensor type to correct field in database
        field_mapping = {
            "temperature": "soil_temp_0_to_7cm",
            "moisture": "moisture",
            "ph": "ph_level",
            "nutrients": ["nitrogen", "phosphorus", "potassium"]
        }

        field_to_update = field_mapping[sensor_type]
        
        # Convert time
        sensor_data["time"] = pd.to_datetime(sensor_data["time"], errors="coerce")

        if isinstance(field_to_update, list):  # If sensor type is "nutrients", multiple fields are updated
            for nutrient, field in zip(sensor_data["value"], field_to_update):
                sensor_data[field] = nutrient
        else:
            sensor_data[field_to_update] = sensor_data["value"]

        # Save data
        save_soil_data(pd.DataFrame([sensor_data]), data_source="sensor")

        return True, "Sensor data processed successfully."
    
    except Exception as e:
        logger.error(f"Error processing sensor data: {e}")
        return False, f"Error processing sensor data: {str(e)}"


def geocode_location(location_name):
    """
    Fetch latitude and longitude for a given location name using OpenCage Geocoder.
    Returns latitude & longitude but logs warnings for low-confidence results.
    """
    try:
        API_KEY = settings.OPENCAGE_API_KEY  # ✅ Use Django settings
        if not API_KEY:
            raise ValueError("Missing OpenCage API Key. Check .env file.")
        url = f"https://api.opencagedata.com/geocode/v1/json?q={location_name}&key={API_KEY}"

        response = requests.get(url)
        response.raise_for_status()

        data = response.json()

        # ✅ Log the full response for debugging
        logger.info(f"Geocoder Response for '{location_name}': {data}")

        if data.get('results'):
            result = data['results'][0]
            coordinates = result['geometry']
            confidence = result.get('confidence', 0)

            # ✅ Log confidence level and proceed even if it's low
            if confidence < 7:
                logger.warning(f"⚠️ Low confidence ({confidence}) geocode result for '{location_name}', but using it anyway.")
            
            logger.info(f"✅ Geocoded '{location_name}' with confidence {confidence}: {coordinates}")

            return {"latitude": coordinates['lat'], "longitude": coordinates['lng']}

        else:
            logger.warning(f"❌ Geocoding failed: No results for location '{location_name}'")
            return None

    except requests.exceptions.RequestException as e:
        logger.error(f"🚨 Geocoding API error: {e}")
        return None
