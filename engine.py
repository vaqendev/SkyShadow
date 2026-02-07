import ee
import os
import json
from google.oauth2.service_account import Credentials

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
        print("🚀 [SUCCESS] Connected to Earth Engine (Analysis Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

# --- 2. THE CORE ANALYSIS ENGINE ---
def analyze_custom_region(geojson: dict):
    """
    Takes a User Drawn Shape (GeoJSON).
    Returns:
      1. A Tile URL (Clipped ONLY to that shape).
      2. Statistics (Calculated for that shape).
    """
    try:
        # A. Define the Region
        region = ee.Geometry(geojson)

        # B. Fetch Data (Landsat 9 + Sentinel 2)
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(region).filterDate('2024-01-01', '2025-01-01').median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-01-01', '2025-01-01').median()

        # C. Calculate Indices
        ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        lst = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('temp')

        # D. Fusion Math
        # We blend them to get the "Heatmap"
        fusion = lst.expression(
            'TEMP - (NDVI * 2.0)', 
            {'TEMP': lst.select('temp'), 'NDVI': ndvi}
        ).rename('fusion_temp')

        # --- E. STATS CALCULATION (Robust Method) ---
        # Instead of sampling points (which fails on clouds), we average the whole area.
        stats = fusion.addBands(ndvi).reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=region,
            scale=30,
            bestEffort=True,
            maxPixels=1e9
        ).getInfo()

        # Extract values safely
        avg_temp = stats.get('fusion_temp', 0)
        avg_ndvi = stats.get('ndvi', 0)

        # Handle "No Data" (e.g., if drawn over ocean/empty space)
        if avg_temp is None: avg_temp = 0
        if avg_ndvi is None: avg_ndvi = 0

        # --- F. VISUAL GENERATION (Clipped) ---
        # 1. Clip the image so it ONLY shows inside the user's shape
        visual_image = fusion.clip(region)

        # 2. Color Palette
        vis_params = {
            'min': 20, 'max': 45,
            'palette': ['006400', '32CD32', 'FFFF00', 'FFA500', 'FF0000', '8B0000']
        }
        
        # 3. Get the URL
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        return {
            "map_url": map_url,
            "stats": {
                "avg_temp": round(avg_temp, 1),
                "avg_ndvi": round(avg_ndvi, 2),
                "risk_score": "Critical" if avg_temp > 38 else "High" if avg_temp > 34 else "Moderate"
            }
        }

    except Exception as e:
        print(f"Analysis Error: {e}")
        return {"error": str(e)}