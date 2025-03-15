import os
from django.conf import settings
import pickle
import dill
import pandas as pd
from weather.models import WeatherData
from soil.models import SoilData
from datetime import datetime, timedelta
from django.utils.timezone import make_aware


# Utility to load models
def load_model(model_name):
    model_path = os.path.join(settings.TRAINED_MODELS_DIR, model_name)
    with open(model_path, "rb") as file:
        model = pickle.load(file)
    return model

# Utility to load the feature engineering pipeline
def load_pipeline(pipeline_name):
    pipeline_path = os.path.join(settings.TRAINED_MODELS_DIR, pipeline_name)
    with open(pipeline_path, "rb") as file:
        pipeline = dill.load(file)
    return pipeline

# Utility to preprocess input data
def preprocess_input_data(input_data, pipeline):
    """
    Preprocesses input data using the provided pipeline.

    Args:
        input_data (pd.DataFrame): Raw input data.
        pipeline: Feature engineering pipeline.

    Returns:
        pd.DataFrame: Processed data ready for predictions.
    """
    print("DEBUG: Preprocessing input data")
    if not isinstance(input_data, pd.DataFrame):
        raise ValueError("Input data must be a pandas DataFrame.")

    print("DEBUG: Input Data Shape Before Processing:", input_data.shape)

    # Add missing columns with default values if needed
    required_columns = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precip_30day_sum"]
    for col in required_columns:
        if col not in input_data.columns:
            input_data[col] = 0  # Default value

    # Use the pipeline to transform the data
    processed_data = pipeline.transform(input_data)
    print("DEBUG: Processed data:", processed_data)
    return processed_data

# Utility to make predictions
def make_predictions(models, input_data):
    """
    Makes predictions using a list of models.

    Args:
        models (dict): A dictionary of models with names as keys and model objects as values.
        input_data (pd.DataFrame): Preprocessed input data.

    Returns:
        dict: Predictions from each model.
    """
    required_columns = ["temperature_2m", "relative_humidity_2m", "wind_speed_10m", "precip_30day_sum"]
    if not all(col in input_data.columns for col in required_columns):
        raise ValueError(f"Input data must contain the following columns: {required_columns}")
    
    predictions = {}
    for model_name, model in models.items():
        predictions[model_name] = model.predict(input_data[required_columns])
    return predictions

# Utility to fetch and merge weather and soil data
def fetch_and_merge_data():
    """
    Fetch and merge weather and soil data for the next 7 days.
    Returns:
        pd.DataFrame: A combined dataset of weather and soil data.
    """
    
    from datetime import datetime, timedelta
    import pandas as pd
    from django.utils.timezone import make_aware

    today = make_aware(datetime.utcnow())  
    next_week = today + timedelta(days=7)

    # Fetch weather data
    weather_queryset = WeatherData.objects.filter(time__gte=today, time__lte=next_week)
    weather_df = pd.DataFrame(list(weather_queryset.values()))

    # Fetch soil data
    soil_queryset = SoilData.objects.filter(time__gte=today, time__lte=next_week)
    soil_df = pd.DataFrame(list(soil_queryset.values()))

    print("DEBUG: Weather Data Count:", len(weather_df))
    print("DEBUG: Soil Data Count:", len(soil_df))

    # If either dataset is empty, print error
    if weather_df.empty:
        print("❌ DEBUG: Weather data is EMPTY!")
    if soil_df.empty:
        print("❌ DEBUG: Soil data is EMPTY!")

    # Merge datasets
    if not weather_df.empty and not soil_df.empty:
        merged_df = pd.merge(weather_df, soil_df, on=["time", "latitude", "longitude"], suffixes=("_weather", "_soil"))
    else:
        merged_df = pd.DataFrame()  # Return empty DataFrame if missing data

    print("DEBUG: Merged Data Count:", len(merged_df))  
    return merged_df.reset_index(drop=True)



import os

def get_model_version(model_name):
    version_file = f"trained_models/{model_name}_version.txt"
    if os.path.exists(version_file):
        with open(version_file, "r") as f:
            return f.read().strip()
    return "Unknown Version"




