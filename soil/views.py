from datetime import datetime
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from django.db.models import Q
from django.http import HttpResponse
import csv
import logging
import pandas as pd
from .models import SoilData
from .serializers import SoilDataSerializer
from .utils import save_soil_data, process_csv_data, process_sensor_data, validate_soil_data, geocode_location
from django.shortcuts import render
from django.utils.dateparse import parse_date
from django.contrib import messages
from django.utils.timezone import localtime
from django.utils.timezone import now
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import math





class SampleCSVDownloadAPIView(APIView):
    def get(self, request):
        """
        Generate and return a sample CSV file for download with all required fields.
        """
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="sample_soil_data.csv"'

        writer = csv.writer(response)

        # ✅ Write CSV header
        writer.writerow(["time", "location", "soil_temp_0_to_7cm", "soil_temp_7_to_28cm", 
                         "latitude", "longitude", "moisture", "ph_level", 
                         "nitrogen", "phosphorus", "potassium"])

        # ✅ Sample data row
        writer.writerow(["2025-02-07T12:00:00Z", "Texas", "18.5", "20.1", 
                         "31.2639", "-98.5456", "12", "6.5", "3", "5", "7"])

        return response
    

# Setup logger
logger = logging.getLogger(__name__)


def soil_dashboard(request):
    """ Render the Soil Data Dashboard Page. """
    soil_data = SoilData.objects.all()
    for data in soil_data:
        data.time = localtime(data.time).strftime("%b. %d, %Y, %I:%M %p")  # Format time to readable format
        data.last_updated = localtime(data.last_updated).strftime("%b. %d, %Y, %I:%M %p")  # Format last_updated
    return render(request, 'soil_dashboard.html', {"soil_data": soil_data})


# ✅ Custom Pagination Class
class SoilDataPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or self.page_size
        total_pages = math.ceil(self.page.paginator.count / page_size)
        return Response({
            'count': self.page.paginator.count,
            'total_pages': total_pages,
            'current_page': self.page.number,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


# ✅ List & Retrieve Soil Data
class SoilDataAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            sort = request.query_params.get("sort", "time")
            order = request.query_params.get("order", "desc")  # ✅ Default to "desc" (newest first)
            start_date = request.query_params.get("start_date")
            end_date = request.query_params.get("end_date")
            location = request.query_params.get("location")

            # ✅ Get data & sort by time (descending order)
            soil_data = SoilData.objects.all().order_by('-time')  # ✅ Default: Newest first

            # ✅ Apply filters if provided
            if start_date:
                start_date = parse_date(start_date)
                soil_data = soil_data.filter(time__date__gte=start_date)
            if end_date:
                end_date = parse_date(end_date)
                soil_data = soil_data.filter(time__date__lte=end_date)
            if location:
                soil_data = soil_data.filter(Q(original_location__icontains=location) | Q(location__icontains=location))

            # ✅ If user wants ascending order, override
            if order == "asc":
                soil_data = soil_data.order_by('time')

            # ✅ Convert time to readable format
            for data in soil_data:
                data.time = localtime(data.time).strftime("%b. %d, %Y, %I:%M %p")
                data.last_updated = localtime(data.last_updated).strftime("%b. %d, %Y, %I:%M %p")

            # ✅ Paginate & return response
            paginator = SoilDataPagination()
            paginated_data = paginator.paginate_queryset(soil_data, request)
            serializer = SoilDataSerializer(paginated_data, many=True)
            return paginator.get_paginated_response(serializer.data)

        except Exception as e:
            logger.error(f"Error fetching soil data: {e}")
            messages.error(request, "Failed to fetch soil data. Please try again later.")
            return Response({"status": "error", "message": "Failed to fetch soil data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Manual Data Entry Endpoint
class ManualSoilDataEntryAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            user = request.user if request.user.is_authenticated else None

            logger.info(f"Received Data in Backend: {data}")

            # ✅ Ensure time is present and valid
            if "time" not in data or not data["time"]:
                data["time"] = now().isoformat()  # ✅ Default to current time if missing
                
            # Validate data
            validation_errors = validate_soil_data(data)
            if validation_errors:
                logger.warning(f"Validation Errors: {validation_errors}")
                return Response({"status": "error", "message": validation_errors}, status=status.HTTP_400_BAD_REQUEST)

            # Ensure location is geocoded if latitude & longitude are missing
            if "latitude" not in data or "longitude" not in data or not data["latitude"] or not data["longitude"]:
                logger.warning(f"Missing coordinates, attempting geolocation for {data['location']}")
                geocode_result = geocode_location(data["location"])
                
                if geocode_result:
                    data["latitude"] = geocode_result["latitude"]
                    data["longitude"] = geocode_result["longitude"]
                else:
                    return Response({"status": "error", "message": "Failed to retrieve latitude & longitude for the location."},
                                    status=status.HTTP_400_BAD_REQUEST)

            # Save data
            save_soil_data(pd.DataFrame([data]), data_source="manual", user=user)
            return Response({"status": "success", "message": "Soil data manually added."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error in manual soil data entry: {e}")
            return Response({"status": "error", "message": f"Failed to save soil data: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ CSV Upload Endpoint
class CSVUploadAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            if "file" not in request.FILES:
                return Response({"status": "error", "message": "No file uploaded."}, status=status.HTTP_400_BAD_REQUEST)

            file = request.FILES["file"]

            # Build a custom folder path: "uploadCSVSOIL/YYYY-MM-DD/username/"
            from datetime import datetime
            import os

            today_str = datetime.now().strftime('%Y-%m-%d')
            username = request.user.username if request.user.is_authenticated else "anonymous"
            # Construct relative upload path (within MEDIA_ROOT)
            upload_dir = os.path.join("uploadCSVSOIL", today_str, username)
            # Create the full directory path under MEDIA_ROOT
            full_upload_dir = os.path.join(settings.MEDIA_ROOT, upload_dir)
            os.makedirs(full_upload_dir, exist_ok=True)
            
            # Create the custom file name with the folder structure
            custom_file_name = os.path.join(upload_dir, file.name)

            # ✅ Save file properly using Django's default storage
            # Save file using Django's default storage
            file_name = default_storage.save(custom_file_name, ContentFile(file.read()))
            file_path = default_storage.path(file_name)

            logger.info(f"File successfully uploaded: {file_path}")

            # ✅ Check if file exists before processing
            if not default_storage.exists(file_name):
                logger.error(f"File not found after saving: {file_path}")
                return Response({"status": "error", "message": "Failed to save file."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # ✅ Process CSV data
            success, message = process_csv_data(file_path, user=request.user)

            if not success:
                return Response({"status": "error", "message": message}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"status": "success", "message": "CSV file uploaded and processed.", "file_url": file_path},
                            status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error uploading CSV: {e}")
            return Response({"status": "error", "message": f"Failed to process CSV file: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ✅ Sensor Data Ingestion Endpoint
class SensorDataIngestionAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            user = request.user if request.user.is_authenticated else None  # Link data to authenticated user

            # Validate and process sensor data
            validation_errors = validate_soil_data(data)
            if validation_errors:
                return Response({"status": "error", "message": validation_errors}, status=status.HTTP_400_BAD_REQUEST)

            process_sensor_data(data, user=user)
            return Response({"status": "success", "message": "Sensor data received successfully."}, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error processing sensor data: {e}")
            return Response({"status": "error", "message": "Failed to process sensor data."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        
        
# ✅ Retrieve, Update, and Delete Specific Soil Data
class SoilDataDetailAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            soil_data = SoilData.objects.get(pk=pk)
            serializer = SoilDataSerializer(soil_data)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except SoilData.DoesNotExist:
            return Response({"status": "error", "message": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, pk):
        try:
            soil_data = SoilData.objects.get(pk=pk)
            serializer = SoilDataSerializer(soil_data, data=request.data, partial=False)  # Full update
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SoilData.DoesNotExist:
            return Response({"status": "error", "message": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

    def patch(self, request, pk):
        """
        Partially update an existing soil record.
        """
        try:
            soil_data = SoilData.objects.get(pk=pk)
            serializer = SoilDataSerializer(soil_data, data=request.data, partial=True)  # Allow partial updates
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except SoilData.DoesNotExist:
            return Response({"status": "error", "message": "Record not found."}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk):
        try:
            soil_data = SoilData.objects.get(pk=pk)
            soil_data.delete()
            return Response({"status": "success", "message": "Record deleted."}, status=status.HTTP_200_OK)
        except SoilData.DoesNotExist:
            return Response({"status": "error", "message": "Record not found."}, status=status.HTTP_404_NOT_FOUND)





# ✅ Fetch Real-Time Soil Data
class SoilDataFetchAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user if request.user.is_authenticated else None  # ✅ Ensure user is passed
            location_name = request.data.get("location_name")
            latitude = request.data.get("latitude")
            longitude = request.data.get("longitude")

            if not location_name and (not latitude or not longitude):
                messages.warning(request, "A location name or coordinates are required.")
                return Response({"status": "error", "message": "A location name or coordinates are required."},
                                status=status.HTTP_400_BAD_REQUEST)
            
            if location_name:
                geocoded = geocode_location(location_name)
                if geocoded:
                    latitude = geocoded['latitude']
                    longitude = geocoded['longitude']
                else:
                    logger.warning(f"Failed to geocode location: {location_name}")
                    messages.warning(request, f"Failed to geocode location: {location_name}")
                    return Response({"status": "error", "message": f"Failed to geocode location: {location_name}"},
                                    status=status.HTTP_400_BAD_REQUEST)

            soil_data = pd.DataFrame({
                "time": [now().isoformat()],  # ✅ Real-time timestamp instead of hardcoded value
                "soil_temp_0_to_7cm": [10.5],
                "soil_temp_7_to_28cm": [12.3],
                "location": [location_name],
                "latitude": [latitude],
                "longitude": [longitude],
            })

            # ✅ Pass user explicitly to store it in the database
            save_soil_data(soil_data, original_location=location_name, user=user)

            messages.success(request, f"Soil data updated successfully for {location_name}.")
            return Response({"status": "success", "message": f"Soil data updated successfully for {location_name}."},
                            status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error fetching live soil data: {e}")
            messages.error(request, "Failed to fetch live soil data. Please try again later.")
            return Response({"status": "error", "message": "Failed to fetch live soil data."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            


# ✅ Export Soil Data as CSV (With Error Handling)
class SoilDataExportAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            location = request.query_params.get("location", "").strip()
            start_date = request.query_params.get("start_date", "").strip()
            end_date = request.query_params.get("end_date", "").strip()
            data_source = request.query_params.get("data_source", "").strip()

            if start_date and not self.is_valid_date(start_date):
                return Response({"status": "error", "message": "❌ Invalid start date format. Use YYYY-MM-DD."}, status=400)

            if end_date and not self.is_valid_date(end_date):
                return Response({"status": "error", "message": "❌ Invalid end date format. Use YYYY-MM-DD."}, status=400)

            soil_data = SoilData.objects.all()
            if location:
                soil_data = soil_data.filter(Q(location__iexact=location) | Q(original_location__iexact=location))
            if start_date and end_date:
                soil_data = soil_data.filter(time__date__range=[start_date, end_date])
            elif start_date:
                soil_data = soil_data.filter(time__date__gte=start_date)
            elif end_date:
                soil_data = soil_data.filter(time__date__lte=end_date)
            if data_source:
                soil_data = soil_data.filter(data_source=data_source)

            if not soil_data.exists():
                return Response({"status": "empty", "message": "⚠️ No data found for the selected filters."}, status=200)

            response = HttpResponse(content_type="text/csv")
            response["Content-Disposition"] = 'attachment; filename="soil_data_filtered.csv"'
            writer = csv.writer(response)

            writer.writerow(["Time", "Location", "Soil Temp (0-7cm)", "Soil Temp (7-28cm)", "Moisture", "pH Level", 
                             "Nitrogen", "Phosphorus", "Potassium", "Latitude", "Longitude", "Data Source"])

            for record in soil_data:
                location_name = record.location if record.location else (record.original_location if record.original_location else "Unknown")

                writer.writerow([
                    record.time, location_name, record.soil_temp_0_to_7cm, record.soil_temp_7_to_28cm,
                    record.moisture, record.ph_level, record.nitrogen, record.phosphorus, record.potassium,
                    record.latitude, record.longitude, record.data_source
                ])

            return response

        except Exception as e:
            logger.error(f"❌ Error exporting soil data: {e}")
            return Response({"status": "error", "message": "❌ Failed to export CSV due to an internal error."}, status=500)





from django.conf import settings  # ✅ Import settings for API Key

class GeocodeAPIView(APIView):
    """
    ✅ Secure Geocoding API: Fetches latitude & longitude from OpenCage API
    """
    def get(self, request):
        try:
            location_name = request.query_params.get("location", "")
            if not location_name:
                return Response({"status": "error", "message": "Location name is required."}, status=status.HTTP_400_BAD_REQUEST)

            geocoded = geocode_location(location_name)
            if geocoded:
                return Response({"status": "success", "latitude": geocoded["latitude"], "longitude": geocoded["longitude"]})
            else:
                return Response({"status": "error", "message": "Failed to geocode location."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            logger.error(f"Error in geocoding API: {e}")
            return Response({"status": "error", "message": "Internal server error."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
