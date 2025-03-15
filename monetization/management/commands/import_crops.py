import csv
from django.core.management.base import BaseCommand
from monetization.models import CropSuitability

class Command(BaseCommand):
    help = "Import crop suitability data from CSV into Django database"

    def handle(self, *args, **kwargs):
        csv_file_path = "crop_suitability_data.csv"  # Update this path if necessary

        with open(csv_file_path, newline='', encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:
                # Convert preferred growing season and suitable soil types into lists
                growing_season = eval(row["preferred_growing_season"])  # Convert string to list
                soil_types = [soil.strip() for soil in row["suitable_soil_types"].split(",")]

                # Build the JSON attributes dynamically
                attributes = {
                    "min_temp": float(row["min_temp"]) if row["min_temp"] else None,
                    "max_temp": float(row["max_temp"]) if row["max_temp"] else None,
                    "min_soil_temp": float(row["min_soil_temp"]) if row["min_soil_temp"] else None,
                    "max_soil_temp": float(row["max_soil_temp"]) if row["max_soil_temp"] else None,
                    "min_pH": float(row["min_pH"]) if row["min_pH"] else None,
                    "max_pH": float(row["max_pH"]) if row["max_pH"] else None,
                    "min_moisture": float(row["min_moisture"]) if row["min_moisture"] else None,
                    "max_moisture": float(row["max_moisture"]) if row["max_moisture"] else None,
                    "max_precipitation": float(row["max_precipitation"]) if row["max_precipitation"] else None,
                    "min_nitrogen": float(row["min_nitrogen"]) if row["min_nitrogen"] else None,
                    "max_nitrogen": float(row["max_nitrogen"]) if row["max_nitrogen"] else None,
                    "min_phosphorus": float(row["min_phosphorus"]) if row["min_phosphorus"] else None,
                    "max_phosphorus": float(row["max_phosphorus"]) if row["max_phosphorus"] else None,
                    "min_potassium": float(row["min_potassium"]) if row["min_potassium"] else None,
                    "max_potassium": float(row["max_potassium"]) if row["max_potassium"] else None,
                }

                # Create or update the crop suitability record
                CropSuitability.objects.update_or_create(
                    name=row["name"],
                    defaults={
                        "crop_type": row["crop_type"],
                        "preferred_growing_season": growing_season,
                        "suitable_soil_types": soil_types,
                        "attributes": attributes,  # Store all crop parameters as JSON
                    }
                )

        self.stdout.write(self.style.SUCCESS("Successfully imported crop suitability data!"))
