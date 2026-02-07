import ee
import os
import json
import requests
from google.oauth2.service_account import Credentials

# --- AUTHENTICATION ---
PROJECT_ID = 'possible-stock-485917-k8' 

# 1. Environment Variable
key_content = os.environ.get("GEE_PRIVATE_KEY")

# 2. Local File Fallback
if not key_content:
    if os.path.exists("credentials.json"):
        print("⚠️ Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

# 3. Initialize
if not key_content:
    print("❌ [CRITICAL] Key Missing!")
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

def analyze_custom_region(geojson: dict, tree_increase: float = 0.0, hotspot_count: int = 5):
    try:
        # A. GEOMETRY GUARD
        region = ee.Geometry(geojson).simplify(maxError=10).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # B. DATA FETCH
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat_col = l9.merge(l8).filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUD_COVER', 40))
        
        if landsat_col.size().getInfo() == 0:
            return {"error": "No clear satellite images found."}

        lst_img = landsat_col.median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median()

        # C. INDICES
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        # D. SIMULATION (Map URL)
        cooling_efficiency = ndbi_raw.multiply(10).add(5).clamp(2, 15)
        cooling_map = cooling_efficiency.multiply(float(tree_increase))
        simulated_lst = lst_raw.subtract(cooling_map)

        visual_image = simulated_lst.clip(region)
        vis_params = {'min': 30, 'max': 45, 'palette': ['00FF00', 'FFFF00', 'FF7F00', 'FF0000'], 'opacity': 0.6}
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # E. HOTSPOTS (THE "SAMPLER" METHOD - Guaranteed Speed)
        hotspots_geojson = []
        try:
            # 1. Normalize
            stats_local = lst_raw.reduceRegion(reducer=ee.Reducer.minMax(), geometry=region, scale=100, bestEffort=True)
            min_temp = ee.Number(stats_local.get('lst_min'))
            max_temp = ee.Number(stats_local.get('lst_max'))
            denom = max_temp.subtract(min_temp).max(0.1)
            lst_norm = lst_raw.subtract(min_temp).divide(denom)
            
            # 2. Priority Score
            priority_score = lst_norm.subtract(ndvi_raw).rename('score')

            # 3. SAMPLE POINTS (The Fix)
            # Instead of heavy vectorization, just grab 500 candidate pixels
            # This ensures we find hotspots even in small manual drawings.
            samples = priority_score.sample(
                region=region,
                scale=70,       # <--- WAS 200, NOW 70
                numPixels=500,  
                geometries=True 
            )

            # 4. FILTER & SORT
            # Sort by score descending (Worst first) and take Top 5
            top_samples = samples.sort('score', False).limit(hotspot_count)

            # 5. CONVERT POINTS TO BOXES
            # We mechanically turn the center-point into a 500m x 500m square
            def point_to_box(feature):
                # Buffer 250m radius -> Square Bounds -> 500m Box
                return feature.buffer(250).bounds()

            top_boxes = top_samples.map(point_to_box)
            
            hotspots_geojson = top_boxes.getInfo()
            print(f"✅ Generated {len(hotspots_geojson.get('features', []))} hotspot boxes.")

        except Exception as e:
            print(f"⚠️ Hotspot Calc Failed: {e}")
            hotspots_geojson = [] 

        # F. STATISTICS
        stats = simulated_lst.addBands(ndvi_raw).addBands(ndbi_raw).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=70, bestEffort=True, maxPixels=1e9
        ).getInfo()

        return {
            "status": "success",
            "map_url": map_url,
            "hotspots": hotspots_geojson,
            "live_temp": get_live_weather(center[1], center[0]),
            "stats": {
                "avg_temp": round(stats.get('lst', 0) or 0, 1),
                "avg_ndvi": round(stats.get('ndvi', 0) or 0, 2),
                "avg_ndbi": round(stats.get('ndbi', 0) or 0, 2)
            }
        }

    except Exception as e:
        print(f"❌ SERVER ERROR DETAILED: {e}")
        return {"error": str(e)}
    
def generate_tree_locations(geojson: dict, temp_drop: float = 0.0):
    # Placeholder for growth simulation
    return {"status": "success", "message": "Growth simulation placeholder"}