#MATHEMATICAL INDICES
## Normalized Difference Vegetation Index (NDVI) = (NIR) - (RED)/ (NIR) + (RED)
## Normalized Difference Built-in Index (NDBI) = (SWIR) - (NIR) / (SWIR) + (NIR)
## Land Surface Temperature (LST) = (DN * 0.00341802 + 149.0) - 273.15
ndvi_raw = s2.normalizedDifference(['B8', 'B4']).rename('ndvi') #s2 => Sentinel-2 image collection
ndbi_raw = s2.normalizedDifference(['B11', 'B8']).rename('ndbi')
lst_raw = lst_img.select('ST_B10').multiply(0.00341802).add(149.0).subtract(273.15).rename('lst') #lst_img => Landsat 8 image collection
