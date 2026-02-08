import ee
import os
import json
import requests
import math 
from google.oauth2.service_account import Credentials

# --- AUTHENTICATION ---
PROJECT_ID = 'my-project-67785-485818' 

key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    if os.path.exists("credentials.json"):
        print("⚠️ Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

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

        # 🟢 DYNAMIC BOX SIZING
        region_area = region.area(maxError=100).getInfo()
        side_length = math.sqrt(region_area)
        dynamic_radius = max(30, min(side_length * 0.05, 2000))
        
        print(f"📏 Region Area: {int(region_area)}m² | Box Radius: {int(dynamic_radius)}m")

        # B. DATA FETCH
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat_col = l9.merge(l8).filterBounds(region).filterDate('2023-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUD_COVER', 40))
        
        if landsat_col.size().getInfo() == 0:
            return {"error": "No clear satellite images found."}

        lst_img = landsat_col.median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2023-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median()

        # C. INDICES
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        # D. SIMULATION
        cooling_efficiency = ndbi_raw.multiply(10).add(5).clamp(2, 15)
        cooling_map = cooling_efficiency.multiply(float(tree_increase))
        simulated_lst = lst_raw.subtract(cooling_map)

        # 🟢 FIX: CALCULATE STATS ON RAW DATA (ANCHOR THE SCALE)
        # We calculate the range based on the *original* temperature, so the scale stays fixed.
        stats_local = lst_raw.reduceRegion( # <--- CHANGED from simulated_lst to lst_raw
            reducer=ee.Reducer.minMax(), 
            geometry=region, 
            scale=200, 
            bestEffort=True
        ).getInfo()

        min_temp_val = stats_local.get('lst_min', 20)
        max_temp_val = stats_local.get('lst_max', 45)

        if max_temp_val - min_temp_val < 5: 
            max_temp_val = min_temp_val + 10

        print(f"🎨 Fixed Palette Range: {min_temp_val:.1f}°C -> {max_temp_val:.1f}°C")

        # E. VISUALIZATION (Green -> Yellow -> Orange -> Red -> Deep Red)
        # Now we apply the *Original* scale to the *Simulated* image.
        # As the image gets cooler, pixels will drop down the color chart.
        visual_image = simulated_lst.clip(region)
        vis_params = {
            'min': min_temp_val, 
            'max': max_temp_val, 
            'palette': ['00FF00', 'FFFF00', 'FFA500', 'FF0000', '8B0000'], 
            'opacity': 0.6
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # F. HOTSPOTS (Clipped)
        hotspots_geojson = []
        try:
            # Re-Normalize (Using fixed range for consistency)
            denom = max_temp_val - min_temp_val
            lst_norm = simulated_lst.subtract(min_temp_val).divide(denom).clamp(0, 1)
            priority_score = lst_norm.subtract(ndvi_raw).rename('score')

            samples = priority_score.sample(region=region, scale=70, numPixels=500, geometries=True)
            top_samples = samples.sort('score', False).limit(hotspot_count)

            def clip_box_to_boundary(feature):
                point_geom = feature.geometry()
                full_box = point_geom.buffer(dynamic_radius).bounds()
                clipped_geometry = full_box.intersection(region, 10)
                return feature.setGeometry(clipped_geometry)

            hotspots_geojson = top_samples.map(clip_box_to_boundary).getInfo()

        except Exception as e:
            print(f"⚠️ Hotspot Calc Failed: {e}")
            hotspots_geojson = [] 

        # G. STATISTICS (On Simulated Data)
        stats = simulated_lst.addBands(ndvi_raw).addBands(ndbi_raw).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=500, bestEffort=True, maxPixels=1e9
        ).getInfo()

        return {
            "status": "success",
            "map_url": map_url,
            "hotspots": hotspots_geojson,
            "live_temp": get_live_weather(center[1], center[0]),
            "range": {"min": min_temp_val, "max": max_temp_val},
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
    return {"status": "success", "message": "Growth simulation placeholder"}