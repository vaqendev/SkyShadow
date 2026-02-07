import ee
import os
import json
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
        print("🚀 [SUCCESS] Connected to Earth Engine (Polygon Analysis Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. ANALYSIS ENGINE ---
def analyze_custom_region(geojson: dict):
    """
    Takes a Multi-Point Polygon -> Returns Summer Heatmap + Stats
    """
    try:
        region = ee.Geometry(geojson)

        # A. FILTER FOR PEAK SUMMER (April - June) to capture Heat Risk
        # We also filter out clouds (>20% cloud cover removed)
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")\
            .filterBounds(region)\
            .filterDate('2024-04-01', '2024-06-30')\
            .filter(ee.Filter.lt('CLOUD_COVER', 20))\
            .median()
        
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")\
            .filterBounds(region)\
            .filterDate('2024-04-01', '2024-06-30')\
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))\
            .median()

        # B. CALCULATION
        ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        lst = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('temp')

        # Fusion (Temp - Cooling Effect)
        fusion = lst.expression(
            'TEMP - (NDVI * 2.0)', 
            {'TEMP': lst.select('temp'), 'NDVI': ndvi}
        ).rename('fusion_temp')

        # C. STATS (Server-Side Reduce)
        # We use a larger scale (100m) for stats to speed up the calculation (less lag)
        stats = fusion.addBands(ndvi).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=100, 
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()

        avg_temp = stats.get('fusion_temp', 0)
        avg_ndvi = stats.get('ndvi', 0)
        
        if avg_temp is None: avg_temp = 0

        # D. VISUALS (Improved Transparency & Colors)
        visual_image = fusion.clip(region)

        vis_params = {
            'min': 30,  # Start Red closer to 30°C
            'max': 50,  # Max out at 50°C
            'palette': ['00FF00', 'FFFF00', 'FF7F00', 'FF0000', '8B0000'], # Green -> Yellow -> Orange -> Red -> Dark Red
            'opacity': 0.6  # <--- 60% Opacity (See roads underneath)
        }
        
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        return {
            "map_url": map_url,
            "stats": {
                "avg_temp": round(avg_temp, 1),
                "avg_ndvi": round(avg_ndvi, 2),
                "risk_score": "Critical" if avg_temp > 42 else "High" if avg_temp > 38 else "Moderate"
            }
        }

    except Exception as e:
        print(f"Analysis Error: {e}")
        return {"error": str(e)}