import ee
import os
import json
import requests
import math 
from google.oauth2.service_account import Credentials

# --- CONFIGURATION ---
PROJECT_ID = 'global-sun-484918-f5' 

# Auth Setup
key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    if os.path.exists("credentials.json"):
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
        print("🚀 Connected to Earth Engine")
    except Exception as e:
        print(f"❌ Auth Error: {e}")

def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url, timeout=1.5).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"

def analyze_custom_region(geojson: dict, tree_increase: float = 0.0, hotspot_count: int = 5):
    try:
        # 1. Geometry & Dynamic Sizing
        region = ee.Geometry(geojson).simplify(maxError=10).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        region_area = region.area(maxError=1000).getInfo()
        side_length = math.sqrt(region_area)
        # Calculate radius relative to city size (clamped 30m - 2000m)
        dynamic_radius = max(30, min(side_length * 0.05, 2000))
        
        # 2. Satellite Data Retrieval
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat_col = l9.merge(l8).filterBounds(region).filterDate('2023-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUD_COVER', 40))
        
        if landsat_col.size().getInfo() == 0:
            return {"error": "No clear satellite images found."}

        lst_img = landsat_col.median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2023-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median()

        # 3. Spectral Indices Calculation
        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        
        # Landsat Thermal conversion (Kelvin to Celsius)
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        # 4. Cooling Simulation
        # Estimate cooling efficiency based on built-up index
        cooling_efficiency = ndbi_raw.multiply(10).add(5).clamp(2, 15)
        cooling_map = cooling_efficiency.multiply(float(tree_increase))
        simulated_lst = lst_raw.subtract(cooling_map)

        # 5. Anchor Scale (Fix range to original data)
        # Using 200m scale for rapid stats calculation
        stats_local = lst_raw.reduceRegion(
            reducer=ee.Reducer.minMax(), 
            geometry=region, 
            scale=200, 
            bestEffort=True
        ).getInfo()

        min_temp = stats_local.get('lst_min', 20)
        max_temp = stats_local.get('lst_max', 45)
        
        # Prevent flat contrast
        if max_temp - min_temp < 5: 
            max_temp = min_temp + 10

        # 6. Visualization Tile Generation
        visual_image = simulated_lst.clip(region)
        vis_params = {
            'min': min_temp, 
            'max': max_temp, 
            'palette': ['00FF00', 'FFFF00', 'FFA500', 'FF0000', '8B0000'], 
            'opacity': 0.6
        }
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # 7. Hotspot Detection
        hotspots_geojson = []
        try:
            # Normalize temp for scoring
            denom = max_temp - min_temp
            lst_norm = simulated_lst.subtract(min_temp).divide(denom).clamp(0, 1)
            priority_score = lst_norm.subtract(ndvi_raw).rename('score')

            # Sample candidates (200m resolution for speed)
            samples = priority_score.sample(
                region=region, 
                scale=200, 
                numPixels=500, 
                geometries=True
            )
            
            top_samples = samples.sort('score', False).limit(hotspot_count)

            # Clip boxes to city boundary
            def clip_box_to_boundary(feature):
                point_geom = feature.geometry()
                full_box = point_geom.buffer(dynamic_radius).bounds()
                clipped_geometry = full_box.intersection(region, 10)
                return feature.setGeometry(clipped_geometry)

            hotspots_geojson = top_samples.map(clip_box_to_boundary).getInfo()

        except Exception as e:
            print(f"Hotspot generation error: {e}")
            hotspots_geojson = [] 

        # 8. Global Statistics
        stats = simulated_lst.addBands(ndvi_raw).addBands(ndbi_raw).reduceRegion(
            reducer=ee.Reducer.mean(), 
            geometry=region, 
            scale=200, 
            bestEffort=True, 
            maxPixels=1e9
        ).getInfo()

        return {
            "status": "success",
            "map_url": map_url,
            "hotspots": hotspots_geojson,
            "live_temp": get_live_weather(center[1], center[0]),
            "range": {"min": min_temp, "max": max_temp},
            "stats": {
                "avg_temp": round(stats.get('lst', 0) or 0, 1),
                "avg_ndvi": round(stats.get('ndvi', 0) or 0, 2),
                "avg_ndbi": round(stats.get('ndbi', 0) or 0, 2)
            }
        }

    except Exception as e:
        print(f"Engine Error: {e}")
        return {"error": str(e)}

def generate_tree_locations(geojson: dict, temp_drop: float = 0.0):
    return {"status": "success", "message": "Growth simulation placeholder"}