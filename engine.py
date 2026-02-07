import ee
import os
import json
import requests
from google.oauth2.service_account import Credentials

# --- AUTHENTICATION ---
PROJECT_ID = 'global-sun-484918-f5' 

# 1. Try to get key from Environment (Railway/Cloud)
key_content = os.environ.get("GEE_PRIVATE_KEY")

# 2. If no Environment key, look for local file (Localhost)
if not key_content:
    if os.path.exists("credentials.json"):
        print("⚠️ Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

# 3. Authenticate
if not key_content:
    print("❌ [CRITICAL] Key Missing! Make sure 'credentials.json' is in the folder.")
else:
    try:
        service_account_info = json.loads(key_content)
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print("🚀 [SUCCESS] Connected to Earth Engine!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url, timeout=1.5).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"

def analyze_custom_region(geojson: dict, tree_increase: float = 0.0):
    try:
        # A. GEOMETRY FIX (Crucial for OSM Data)
        # .simplify(100): Reduces vertex count to prevent payload timeouts
        # .buffer(distance=0, maxError=1): Repairs self-intersecting polygons with required tolerance
        region = ee.Geometry(geojson).simplify(maxError=100).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # B. FETCH ROBUST DATA (L8 + L9 MERGE)
        # We combine Landsat 8 and 9 to double the chance of finding clear images
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        
        # Merge and Filter (Jan-May for clear skies in India)
        landsat_col = l9.merge(l8) \
            .filterBounds(region) \
            .filterDate('2024-03-01', '2024-08-30') \
            .filter(ee.Filter.lt('CLOUD_COVER', 30)) # Relaxed to 30%
        
        # Check if we found anything
        count = landsat_col.size().getInfo()
        if count == 0:
            print("⚠️ Zero images found for this region/date.")
            return {"error": "No clear satellite images found (Clouds > 30%). Try a different region."}

        # Sentinel-2 for Vegetation
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED") \
            .filterBounds(region) \
            .filterDate('2024-03-01', '2024-08-30') \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)) \
            .median()

        # Median Composite for Temp
        lst_img = landsat_col.median()

        # C. INDICES
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        
        # LST Calculation (Landsat 8/9 Band 10 is standard)
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        # D. SIMULATION
        cooling_map = ee.Image.constant(float(tree_increase)).multiply(12.0)
        simulated_lst = lst_raw.subtract(cooling_map)

        # E. VISUALIZATION
        visual_image = simulated_lst.clip(region)
        vis_params = {
            'min': 30, 'max': 45, 
            'palette': ['00FF00', 'FFFF00', 'FF7F00', 'FF0000'],
            'opacity': 0.6
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # F. STATISTICS
        # scale=250 is faster/safer for large cities than 100
        stats = simulated_lst.addBands(ndvi_raw).addBands(ndbi_raw).reduceRegion(
            reducer=ee.Reducer.mean(), 
            geometry=region, 
            scale=250, 
            bestEffort=True, 
            maxPixels=1e9
        ).getInfo()

        avg_temp = stats.get('lst', 0)
        avg_ndvi = stats.get('ndvi', 0)
        avg_ndbi = stats.get('ndbi', 0)

        # Handle nulls if area was fully masked
        if avg_temp is None: avg_temp = 0
        if avg_ndvi is None: avg_ndvi = 0
        if avg_ndbi is None: avg_ndbi = 0

        print(f"✅ Success: {map_url}")
        
        return {
            "status": "success",
            "map_url": map_url,
            "live_temp": get_live_weather(center[1], center[0]),
            "stats": {
                "avg_temp": round(avg_temp, 1),
                "avg_ndvi": round(avg_ndvi, 2),
                "avg_ndbi": round(avg_ndbi, 2)
            }
        }

    except Exception as e:
        print(f"❌ SERVER ERROR DETAILED: {e}")
        return {"error": str(e)}

def generate_tree_locations(geojson: dict, temp_drop: float = 0.0):
    # (Keep your existing generate_tree_locations function here if needed)
    pass