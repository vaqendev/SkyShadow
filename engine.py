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
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print("🚀 [SUCCESS] Connected to Earth Engine (Stable Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. LIVE WEATHER FETCH ---
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url, timeout=1.5).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"

# --- 3. ANALYSIS ENGINE ---
def analyze_custom_region(geojson: dict):
    try:
        # A. GEOMETRY
        region = ee.Geometry(geojson).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # B. DATA FETCH (FULL YEAR 2025 MEDIAN)
        # Using annual median removes winter/summer outliers for a stable "Avg Temp"
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2") \
            .filterBounds(region) \
            .filterDate('2025-01-01', '2025-12-31') \
            .median() 

        # C. INDICES
        # NDVI (Vegetation) & NDBI (Concrete)
        ndvi = l9.normalizedDifference(['SR_B5', 'SR_B4']).rename('ndvi')
        ndbi = l9.normalizedDifference(['SR_B6', 'SR_B5']).rename('ndbi')
        
        # LST (Temp): Kelvin -> Celsius
        lst_raw = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        combined_image = ee.Image([ndvi, ndbi, lst_raw])

        # D. DATA MINING (Fetch Raw Pixels for Client-Side Rendering)
        # We fetch 1500 points to create a dense 2D grid
        samples = combined_image.addBands(ee.Image.pixelLonLat()).sample(
            region=region,
            scale=30,      # Native Landsat Resolution
            numPixels=1500,
            geometries=True 
        )
        
        data_list = samples.getInfo()['features']
        
        if not data_list:
            return {"error": "No valid pixels found."}

        # E. ML TRAINING
        df = pd.DataFrame([f['properties'] for f in data_list])
        df = df.dropna()

        if df.empty:
            return {"error": "Insufficient data for ML."}

        # Train: Temp = f(NDVI, NDBI)
        X = df[['ndvi', 'ndbi']]
        y = df['lst']
        model = LinearRegression()
        model.fit(X, y)

        # F. PREPARE POINTS PAYLOAD
        # We send these points to the frontend to draw the 2D Heatmap Grid
        points_payload = []
        for index, row in df.iterrows():
            coords = data_list[index]['geometry']['coordinates']
            points_payload.append({
                "coordinates": coords,
                "ndvi": round(row['ndvi'], 3),
                "ndbi": round(row['ndbi'], 3),
                "temp": round(row['lst'], 1)
            })

        return {
            "status": "success",
            "live_temp": get_live_weather(center[1], center[0]),
            "ml_model": {
                "coefficients": {
                    "ndvi_slope": float(model.coef_[0]),
                    "base_intercept": float(model.intercept_)
                }
            },
            "points": points_payload, # <--- The data for the dynamic grid
            "stats": {
                "avg_temp_observed": round(df['lst'].mean(), 1),
                "avg_ndvi_observed": round(df['ndvi'].mean(), 2)
            }
        }

    except Exception as e:
        print(f"Server Error Log: {e}")
        return {"error": str(e)}