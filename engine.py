import ee
import os
import json
import requests
from google.oauth2.service_account import Credentials
from functools import lru_cache

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
        print("🚀 [SUCCESS] Connected to Earth Engine (Simulation Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. LIVE WEATHER FETCH (Current Temp) ---
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"

# --- 3. ANALYSIS ENGINE (With Simulation) ---
def analyze_custom_region(geojson: dict, tree_increase: float = 0.0):
    """
    tree_increase: Float 0.0 to 0.5 (Represents 0% to 50% more trees)
    """
    try:
        region = ee.Geometry(geojson)
        center = region.centroid().coordinates().getInfo() # [Lon, Lat]

        # A. SATELLITE DATA (Summer 2024 for Peak Heat Risk)
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(region).filterDate('2024-04-01', '2024-06-30').filter(ee.Filter.lt('CLOUD_COVER', 20)).median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-04-01', '2024-06-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).median()

        # B. BASE INDICES
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi_raw')
        lst_raw = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst_raw')

        # --- C. THE SIMULATION MATH (Realistic Constraints) ---
        # 1. Cap the increase: You can't plant trees on 100% of a city. 
        #    If existing NDVI is low (0.1), max potential is +0.2. If it's mid (0.3), max is +0.4.
        #    We assume 'tree_increase' is the user's *desired* effort.
        
        simulated_ndvi = ndvi_raw.expression(
            'min(NDVI + INCREASE, NDVI + 0.3, 0.7)', # Rule: Max increase +0.3, Absolute Max 0.7 (Forest)
            {'NDVI': ndvi_raw, 'INCREASE': tree_increase}
        ).rename('sim_ndvi')

        # 2. Calculate Cooling: 10% more trees (0.1 NDVI) ≈ 1.5°C cooling
        cooling_effect = simulated_ndvi.subtract(ndvi_raw).multiply(15.0) # 0.1 delta * 15 = 1.5 deg drop

        # 3. Apply Cooling to Temperature
        #    Also subtract 4.0°C globally to convert Surface Temp -> Air Temp
        final_temp = lst_raw.subtract(cooling_effect).subtract(4.0).rename('final_temp')

        # --- D. STATS ---
        stats = final_temp.addBands(simulated_ndvi).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=100, bestEffort=True, maxPixels=1e9
        ).getInfo()

        avg_temp = stats.get('final_temp', 0)
        avg_ndvi = stats.get('sim_ndvi', 0)
        
        # --- E. LIVE WEATHER ---
        live_temp = get_live_weather(center[1], center[0])

        # --- F. VISUALS ---
        # We render the SIMULATED temperature.
        # If user adds trees, the map will actually turn Green/Yellow (Cooler).
        visual_image = final_temp.clip(region)
        vis_params = {
            'min': 28, 'max': 45, 
            'palette': ['00FF00', 'FFFF00', 'FF7F00', 'FF0000', '8B0000'], 
            'opacity': 0.6
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        return {
            "map_url": map_url,
            "live_temp": live_temp,
            "stats": {
                "avg_temp": round(avg_temp, 1),
                "avg_ndvi": round(avg_ndvi, 2),
                "risk_score": "Critical" if avg_temp > 40 else "High" if avg_temp > 35 else "Moderate"
            }
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}