from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from fastapi.middleware.cors import CORSMiddleware
import engine 

app = FastAPI()

# --- CORS SETUP (Essential for Frontend Access) ---
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],
)

# --- REQUEST MODEL ---
# Note: We removed 'tree_increase'. 
# The backend now calculates the *physics equation* of the area.
# The frontend will use that equation to apply the tree increase locally.
class AnalysisRequest(BaseModel):
    geojson: Dict[str, Any]

@app.get("/")
def read_root():
    return {"status": "SkyShadow Backend is Running", "docs_url": "/docs"}

@app.post("/analyze")
def analyze_region(request: AnalysisRequest):
    """
    1. Receives the Polygon (GeoJSON) from the frontend.
    2. Calls the ML Engine to mine data & train the regression model.
    3. Returns the Coefficients (Slope/Intercept) + Base Map Tile.
    """
    
    result = engine.analyze_custom_region(request.geojson)
    
    # Handle GEE or Server Errors
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return result