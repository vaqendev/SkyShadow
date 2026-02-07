# This code calculates a priority score for hotspots based on land surface temperature (LST) and normalized difference vegetation index (NDVI).
# It normalizes the LST values and subtracts the NDVI values to create a score that can be used to identify areas of concern.
stats_local = lst_raw.reduceRegion(reducer=ee.Reducer.minMax(), geometry=region, scale=500, bestEffort=True)
min_temp = ee.Number(stats_local.get('lst_min'))
max_temp = ee.Number(stats_local.get('lst_max'))
denom = max_temp.subtract(min_temp).max(0.1)
lst_norm = lst_raw.subtract(min_temp).divide(denom)
priority_score = lst_norm.subtract(ndvi_raw).rename('score')

# DYNAMIC BOX SIZING LOGIC
# Calculate approximate area in sq meters
region_area = region.area(maxError=1000).getInfo()
# Derive a "Characteristic Length" (side of the square equivalent)
side_length = math.sqrt(region_area)
# Set box size to roughly 5% of the region's width (1/20th)
# This ensures boxes grow/shrink with your drawing.
dynamic_radius = side_length * 0.05
# Clamp results to keep them sane (Min 30m radius, Max 2000m radius)
dynamic_radius = max(30, min(dynamic_radius, 2000))