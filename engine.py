import ee
import os
import json
import requests
from google.oauth2.service_account import Credentials


PROJECT_ID = 'possible-stock-485917-k8' 

key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    if os.path.exists("credentials.json"):
        print(" Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

if not key_content:
    print(" Key Missing ")
else:
    try:
        service_account_info = json.loads(key_content)
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print(" [SUCCESS] Connected to Earth Engine!")
    except Exception as e:
        print(f" Auth Error: {e}")


def analyze_custom_region(geojson: dict, tree_increase: float = 0.0):
    # try:
        
        region = ee.Geometry(geojson).simplify(maxError=100).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # Data fetch from satellite 
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat_col = l9.merge(l8).filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUD_COVER', 40))

        
        if landsat_col.size().getInfo() == 0:
            return {"error": "No clear satellite images found."}

        lst_img = landsat_col.median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median()

        # maths formulas for converting satellite bands into data

        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')
