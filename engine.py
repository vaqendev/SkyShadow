import ee
import os
import json
import requests
import math
from google.oauth2.service_account import Credentials


PROJECT_ID = 'possible-stock-485917-k8' 

key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    if os.path.exists("credentials.json"):
        print(" Running Locally: Loading credentials.json")
        with open("credentials.json", "r") as f:
            key_content = f.read()

if not key_content:
    print(" Key Missing ")
else:
    try:
        service_account_info = json.loads(key_content)
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print(" [SUCCESS] Connected to Earth Engine!")
    except Exception as e:
        print(f" Auth Error: {e}")

def get_live_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m"
        res = requests.get(url, timeout=1.5).json()
        return res['current']['temperature_2m']
    except:
        return "N/A"        




def analyze_custom_region(geojson: dict, tree_increase: float = 0.0):
    try:
        
        region = ee.Geometry(geojson).simplify(maxError=100).buffer(distance=0, maxError=1)
        center = region.centroid().coordinates().getInfo()

        # Data fetch from satellite 
        l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2")
        l8 = ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        landsat_col = l9.merge(l8).filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUD_COVER', 40))

        
        if landsat_col.size().getInfo() == 0:
            return {"error": "No clear satellite images found."}

        lst_img = landsat_col.median()
        s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(region).filterDate('2024-01-01', '2024-05-30').filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).median()

        # maths formulas for converting satellite bands into data

        ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
        ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
        lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst')

        # fetching and loading of map_tile url and its colour palette
        cooling_efficiency = ndbi_raw.multiply(10).add(5).clamp(2, 15)
        cooling_map = cooling_efficiency.multiply(float(tree_increase))
        simulated_lst = lst_raw.subtract(cooling_map)

        visual_image = simulated_lst.clip(region)
        vis_params = {'min': 30, 'max': 45, 'palette': ['00FF00', 'FFFF00', 'FF7F00', 'FF0000'], 'opacity': 0.6}
        map_url = visual_image.getMapId(vis_params)['tile_fetcher'].url_format

        # defining thermal hotspots 
        hotspots_geojson = []
        try:
            # defining a priority score for thermal hotspots region to rank them based on their criticality
            stats_local = lst_raw.reduceRegion(reducer=ee.Reducer.minMax(), geometry=region, scale=300, bestEffort=True)
            min_temp = ee.Number(stats_local.get('lst_min'))
            max_temp = ee.Number(stats_local.get('lst_max'))
            denom = max_temp.subtract(min_temp).max(0.1)
            lst_norm = lst_raw.subtract(min_temp).divide(denom)
            priority_score = lst_norm.subtract(ndvi_raw).rename('score')


            # taking random points and computing priority score for these random points and sorting/ranking them and fetching their top 10
            samples = priority_score.sample(
                    region=region,
                    scale=200,      
                    numPixels=500,  
                    geometries=True 
                )
            top_samples = samples.sort('score', False).limit(10) # Get top 10 for the slider

            # dynamic bounding box for thermal hotspot region
            region_area = region.area(maxError=300).getInfo()
            side_length = math.sqrt(region_area)
            # box size to roughly 5% of the region's width 
            dynamic_radius = side_length * 0.05
            #  Clamp results to keep them sane (Min 30m radius, Max 2000m radius)
            dynamic_radius = max(30, min(dynamic_radius, 2000))
            def point_to_box(feature):
                # Uses the dynamic_radius calculated from the user's polygon area
                return feature.buffer(dynamic_radius).bounds()
        
        except Exception as e:
            print(f" Hotspot Calc Failed: {e}")
            hotspots_geojson = [] 
        
        # stats and its return to frontend as response
        stats = simulated_lst.addBands(ndvi_raw).addBands(ndbi_raw).reduceRegion(
            reducer=ee.Reducer.mean(), geometry=region, scale=150, bestEffort=True, maxPixels=1e9
        ).getInfo()
        
        avg_temp = stats.get('lst', 0) or 0
        avg_ndvi = stats.get('ndvi', 0) or 0
        avg_ndbi = stats.get('ndbi', 0) or 0

        return {
            "status": "success",
            "map_url": map_url,
            "hotspots": hotspots_geojson, 
            "live_temp": get_live_weather(center[1], center[0]),
            "stats": {
                "avg_temp": round(avg_temp, 1),
                "avg_ndvi": round(avg_ndvi, 2),
                "avg_ndbi": round(avg_ndbi, 2)
            }
        }

    except Exception as e:
        print(f" SERVER ERROR DETAILED: {e}")
        return {"error": str(e)}




