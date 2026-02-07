import ee
import os
import json
import math
from functools import lru_cache
from google.oauth2.service_account import Credentials

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
        print("🚀 [SUCCESS] Connected to Earth Engine (Production Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

@lru_cache(maxsize=100)
def generate_heatmap_grid(center_lat: float, center_lon: float, radius_km: int = 5):
    safe_scale = max(30, int(radius_km * 25)) 
    roi = ee.Geometry.Point([center_lon, center_lat]).buffer(radius_km * 1000).bounds()

    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterBounds(roi).filterDate('2024-01-01', '2025-01-01').median()
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(roi).filterDate('2024-01-01', '2025-01-01').median()
    
    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
    lst = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('temp_raw')

    combined = lst.addBands(ndvi)
    
    try:
        samples = combined.sample(
            region=roi, scale=safe_scale, geometries=True, numPixels=4000
        ).getInfo()
    except:
        return []

    flat_list = []
    features = samples.get('features', [])
    for item in features:
        props = item['properties']
        t_val = props.get('temp_raw', 35)
        n_val = props.get('ndvi', 0)
        
        if t_val is None or t_val > 60 or t_val < -10: continue

        final_temp = t_val
        if n_val > 0.4: final_temp = t_val - 1.5 

        flat_list.append({"temp": final_temp, "ndvi": n_val})

    return flat_list

def get_city_stats(lat: float, lon: float):
    try:
        data = generate_heatmap_grid(lat, lon, radius_km=5)
        
        if not data: return {"avg_temp": 0, "error": "No data"}
        
        temps = [d['temp'] for d in data]
        ndvis = [d['ndvi'] for d in data]
        avg_t = sum(temps) / len(temps)
        avg_n = sum(ndvis) / len(ndvis)
        
        return {
            "city_center": {"lat": lat, "lon": lon},
            "stats": {
                "avg_temp_celsius": round(avg_t, 1),
                "avg_ndvi_index": round(avg_n, 3),
                "green_cover_percent": f"{int(avg_n * 100)}%",
                "risk_score": "Critical" if avg_t > 38 else "High" if avg_t > 34 else "Moderate"
            }
        }
    except Exception as e:
        print(f"Stats Error: {e}")
        return {"avg_temp": 0, "error": str(e)}

def get_tile_url():
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate('2024-01-01', '2025-01-01').median()
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate('2024-01-01', '2025-01-01').median()

    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
    lst = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('temp')

    fusion = lst.expression('TEMP - (NDVI * 2.5)', {'TEMP': lst.select('temp'), 'NDVI': ndvi}).rename('fusion_temp')

    vis_params = {
        'min': 20, 'max': 45,
        'palette': ['006400', '32CD32', 'FFFF00', 'FFA500', 'FF0000', '8B0000']
    }
    
    return fusion.getMapId(vis_params)['tile_fetcher'].url_format