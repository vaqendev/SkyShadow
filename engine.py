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
        print("🚀 [SUCCESS] Connected to Earth Engine (Smart Growth Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. LIVE WEATHER FETCH ---
def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url, timeout=2).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"

# --- 3. ANALYSIS ENGINE (Context-Aware) ---
def analyze_custom_region(geojson: dict, tree_increase: float = 0.0):
    try:
        region = ee.Geometry(geojson)
        center = region.centroid().coordinates().getInfo()

        # A. DATA (Summer 2024)
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(region).filterDate('2024-04-01', '2024-06-30').filter(ee.Filter.lt('CLOUD_COVER', 25)).median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-04-01', '2024-06-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 25)).median()

        # B. BASE INDICES
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi_raw')
        lst_raw = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst_raw')

        # --- C. SMART GROWTH LOGIC (The "Concrete Ceiling") ---
        # 1. Define the effort (User Slider)
        effort = ee.Image(tree_increase)

        # 2. Apply Constraints based on CURRENT land type
        # If Concrete (NDVI < 0.15): Only 20% effective (Street trees)
        # If Mixed (NDVI < 0.3): 60% effective (Gardens)
        # If Open (NDVI >= 0.3): 100% effective (Forests)
        
        real_increase = effort.where(ndvi_raw.lt(0.15), effort.multiply(0.2))\
                              .where(ee.Filter.And([ndvi_raw.gte(0.15), ndvi_raw.lt(0.3)]), effort.multiply(0.6))

        # 3. Calculate New NDVI (Capped at 0.7 for biology constraints)
        simulated_ndvi = ndvi_raw.add(real_increase).min(0.7).rename('sim_ndvi')

        # 4. Cooling Math (Conservative: 12.0 slope)
        cooling_effect = simulated_ndvi.subtract(ndvi_raw).multiply(12.0)
        final_temp = lst_raw.subtract(cooling_effect).subtract(4.0).rename('final_temp')

        # --- D. STATS ---
        stats = final_temp.addBands(simulated_ndvi).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=100, bestEffort=True, maxPixels=1e9
        ).getInfo()

        avg_temp = stats.get('final_temp') or 0.0
        avg_ndvi = stats.get('sim_ndvi') or 0.0

        # --- E. VISUALS (Cyber Palette) ---
        # Cyan (Cool/Safe) -> Green -> Yellow -> Orange -> Red (Hot/Critical)
        visual_image = final_temp.clip(region)
        vis_params = {
            'min': 28, 
            'max': 44, 
            'palette': [
                '00FFFF', # Cyan (Deep Cool / High Veg)
                '00FF00', # Neon Green (Safe)
                'FFFF00', # Yellow (Caution)
                'FF7F00', # Orange (High Heat)
                'FF0000', # Red (Critical)
                '800020'  # Burgundy (Extreme)
            ], 
            'opacity': 0.65
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format
        live_temp = get_live_weather(center[1], center[0])

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