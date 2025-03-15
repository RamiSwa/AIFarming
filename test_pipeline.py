import dill
import pandas as pd

# Load pipeline
with open("/app/trained_models/feature_engineering_pipeline.pkl", "rb") as file:
    pipeline = dill.load(file)

# Test input
input_data = pd.DataFrame([
    {
        "time": "2023-01-15T08:00:00Z",
        "temperature_2m": 10.5,
        "relative_humidity_2m": 85,
        "wind_speed_10m": 5.5,
        "precipitation": 1.2
    }
])

# Process input data
processed_data = pipeline.transform(input_data)
print("Processed Data:", processed_data)
