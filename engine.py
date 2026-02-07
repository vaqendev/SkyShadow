import ee
import os
import json
from functools import lru_cache
from google.oauth2.service_account import Credentials

PROJECT_ID = 'global-sun-484918-f5' 

key_content = os.environ.get("GEE_PRIVATE_KEY")
if not key_content:
    def dummy_init(): pass
else:
    try:
        service_account_info = json.loads(key_content)
        SCOPES = ['https://www.googleapis.com/auth/earthengine']
        creds = Credentials.from_service_account_info(service_account_info, scopes=SCOPES)
        ee.Initialize(credentials=creds, project=PROJECT_ID)
        print("🚀 [SUCCESS] Connected to Earth Engine (Tile Mode)!")
    except Exception as e:
        print(f"❌ [CRITICAL] Auth Error: {e}")

@lru_cache(maxsize=10) 
def get_tile_url():
    s2 = ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterDate('2024-01-01', '2025-01-01').median()
    
    l9 = ee.ImageCollection("LANDSAT/LC09/C02/T1_L2").filterDate('2024-01-01', '2025-01-01').median()

    ndvi = s2.normalizedDifference(['B8', 'B4']).rename('ndvi')
    lst = l9.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('temp')

    fusion = lst.expression(
        'TEMP - (NDVI * 2.5)',
        {'TEMP': lst.select('temp'), 'NDVI': ndvi}
    ).rename('fusion_temp')

    vis_params = {
        'min': 20,    
        'max': 45,    
        'palette': [
            '006400', 
            '32CD32', 
            'FFFF00', 
            'FFA500', 
            'FF0000', 
            '8B0000'  
        ]
    }

    map_id_dict = fusion.getMapId(vis_params)
    
    return map_id_dict['tile_fetcher'].url_format