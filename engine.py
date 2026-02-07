import ee
import os
import json
import requests
import pandas as pd
import numpy as np
from google.oauth2.service_account import Credentials
from sklearn.linear_model import LinearRegression

# --- 1. AUTHENTICATION ---
PROJECT_ID = 'global-sun-484918-f5' 
key_content = os.environ.get("GEE_PRIVATE_KEY")

if not key_content:
    print("❌ [CRITICAL] GEE_PRIVATE_KEY Missing")
else:
    try:
        service_account_info = json.loads(key_content)
        # Standard GEE Scopes
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print("🚀 [SUCCESS] Connected to Earth Engine!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. LIVE WEATHER FETCH ---
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        return requests.get(url, timeout=1.5).json()['current']['temperature_2m']
    except:
        return "N/A"

# --- 3. ANALYSIS ENGINE ---
def analyze_custom_region(geojson: dict):
    try:
        # A. GEOMETRY SETUP
        # Buffer(0,1) fixes topology errors instantly
        region = ee.Geometry(geojson).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # B. DATA FETCH (TARGETING SUMMER FOR CORRECT PHYSICS)
        # We use Summer 2024 (April-June) to capture "Heatwave" conditions.
        # This ensures trees are cooler than concrete, fixing the ML logic.
        # .sort('CLOUD_COVER').first() grabs the single clearest day.
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
            .filterBounds(region) \
            .filterDate('2024-04-01', '2024-06-30') \
            .sort('CLOUD_COVER') \
            .first()

        # C. INDICES CALCULATION
        # NDVI (Vegetation)
        ndvi = l9.normalizedDifference(['SR_B5', 'SR_B4']).rename('ndvi')
        # NDBI (Infrastructure/Concrete)
        ndbi = l9.normalizedDifference(['SR_B6', 'SR_B5']).rename('ndbi')
        # LST (Land Surface Temp) - Converted to Celsius
        lst_raw = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')
        
        combined = ee.Image([ndvi, ndbi, lst_raw])

        # D. GENERATE MAP TILE URL (The "Base Layer")
        # We restore this so you have the beautiful static heatmap underneath the dots.
        visual_image = lst_raw.clip(region)
        vis_params = {
            'min': 30, 'max': 50,  # Adjusted for Summer Temps (Hotter = Red)
            'palette': ['0000ff', '00ffff', 'ffff00', 'ff0000'], # Blue->Cyan->Yellow->Red
            'opacity': 0.6
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # E. FETCH RAW PIXELS (The "Simulation Dots")
        # 2500 pixels gives a dense, high-resolution grid for the simulation.
        samples = combined.addBands(ee.Image.pixelLonLat()).sample(
            region=region, 
            scale=30, 
            numPixels=2500, 
            geometries=True 
        )
        
        data_list = samples.getInfo()['features']
        if not data_list: return {"error": "No valid pixels found (Cloud/Water?)."}

        # Prepare Data for ML
        df = pd.DataFrame([f['properties'] for f in data_list]).dropna()
        if df.empty: return {"error": "Insufficient clean data for ML."}

        # F. ML TRAINING (Context-Aware Physics)
        # We learn the relationship: Temp = a(Vegetation) + b(Concrete) + c
        X = df[['ndvi', 'ndbi']]
        y = df['lst']
        
        model = LinearRegression()
        model.fit(X, y)

        # DEBUG: Print the learned physics to console logs
        print(f"DEBUG: Model Slopes -> NDVI: {model.coef_[0]}, NDBI: {model.coef_[1]}")

        # G. PREPARE CLIENT PAYLOAD
        points_payload = []
        for index, row in df.iterrows():
            points_payload.append({
                "coordinates": data_list[index]['geometry']['coordinates'],
                "ndvi": round(row['ndvi'], 3),
                "ndbi": round(row['ndbi'], 3),
                "temp": round(row['lst'], 1)
            })

        return {
            "status": "success",
            "map_url": map_url,  # Sending the Tile URL back
            "live_temp": get_live_weather(center[1], center[0]),
            "ml_model": {
                "coefficients": {
                    "ndvi_slope": float(model.coef_[0]), # The Cooling Factor
                    "base_intercept": float(model.intercept_)
                }
            },
            "points": points_payload, # The Simulation Grid
            "stats": {
                "avg_temp": round(df['lst'].mean(), 1),
                "avg_ndvi": round(df['ndvi'].mean(), 2),
                "avg_ndbi": round(df['ndbi'].mean(), 2)
            }
        }

    except Exception as e:
        print(f"Server Error: {e}")
        return {"error": str(e)}